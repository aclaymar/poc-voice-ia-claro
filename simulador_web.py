import streamlit as st
import boto3
import json
from elevenlabs.client import ElevenLabs
import os
import base64
import time
import requests
from streamlit_mic_recorder import mic_recorder

# 1. Configuração Inicial
st.set_page_config(page_title="AVI Claro - Pós-Venda", page_icon="📞")

# --- ESTILO CLARO (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #ee1d23 !important; }
    h1, h2, h3, p, span, label, .stMarkdown { color: white !important; }
    .stTextInput>div>div>input { color: black !important; border-radius: 10px; }
    .stButton>button { background-color: white !important; color: #ee1d23 !important; border-radius: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE APIs E CLIENTES AWS ---
try:
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"])
    
    # Credenciais compartilhadas
    aws_auth = {
        "aws_access_key_id": st.secrets["AWS_ACCESS_KEY"],
        "aws_secret_access_key": st.secrets["AWS_SECRET_KEY"],
        "region_name": "us-east-1"
    }

    bedrock = boto3.client(service_name='bedrock-runtime', **aws_auth)
    s3_client = boto3.client('s3', **aws_auth)
    transcribe_client = boto3.client('transcribe', **aws_auth)

except Exception as e:
    st.error(f"Erro na inicialização: Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES CORE ---

def transcrever_audio_aws(audio_bytes):
    """Sobe o áudio para o S3 e usa o Transcribe para converter em texto"""
    job_name = f"transcricao_{int(time.time())}"
    bucket_name = "audio-claro-poc-andy" 
    file_name = f"{job_name}.webm"

    try:
        # 1. Upload para S3
        s3_client.put_object(Bucket=bucket_name, Key=file_name, Body=audio_bytes)
        
        # 2. Inicia Transcrição
        job_uri = f"s3://{bucket_name}/{file_name}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat='webm',
            LanguageCode='pt-BR'
        )

        # 3. Aguarda o resultado (Polling)
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            time.sleep(1)

        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            result_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            response = requests.get(result_url)
            return response.json()['results']['transcripts'][0]['transcript']
    except Exception as e:
        st.error(f"Erro no processo AWS: {e}")
    return None

def tocar_audio(texto):
    try:
        audio = client_eleven.text_to_speech.convert(
            text=texto,
            voice_id="RGymW84CSmfVugnA5tvA", 
            model_id="eleven_turbo_v2_5" 
        )
        audio_bytes = b"".join(audio)
        b64 = base64.b64encode(audio_bytes).decode()
        md = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ElevenLabs: {e}")

def obter_resposta_ia(pergunta):
    try:
        prompt_sistema = "Você é o AVI, o assistente virtual de pós-venda da Claro. Seja cordial, direto e resolutivo. Use no máximo 3 frases por resposta."
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "system": prompt_sistema,
            "messages": [{"role": "user", "content": pergunta}]
        })
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except Exception as e:
        return f"Erro no Bedrock: {e}"

# --- INTERFACE DO USUÁRIO ---
st.title("📞 AVI - Assistente Virtual Claro")
st.subheader("Showcase Pós-Venda - AWS Infrastructure")

st.markdown("---")
st.write("### 🎙️ Fale com o AVI")
audio_gravado = mic_recorder(
    start_prompt="🔴 Iniciar Conversa por Voz",
    stop_prompt="🟢 Enviar Áudio",
    key='recorder'
)

st.markdown("### ⌨️ Ou digite sua dúvida")
pergunta_texto = st.text_input("Como posso ajudar?", placeholder="Ex: Onde está meu iPhone?")

pergunta_final = None

# LÓGICA DE PROCESSAMENTO
if audio_gravado:
    with st.spinner("Amazon Transcribe processando sua voz..."):
        pergunta_final = transcrever_audio_aws(audio_gravado['bytes'])
        if pergunta_final:
            st.success(f"Você disse: {pergunta_final}")

elif st.button("Enviar Texto") and pergunta_texto:
    pergunta_final = pergunta_texto

if pergunta_final:
    with st.spinner("O AVI está processando sua resposta..."):
        resposta = obter_resposta_ia(pergunta_final)
        st.chat_message("assistant").write(resposta)
        tocar_audio(resposta)