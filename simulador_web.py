import streamlit as st
import boto3  # Adicionado para AWS
import json
from elevenlabs.client import ElevenLabs
import os
import base64
import time

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

# --- INICIALIZAÇÃO DE APIs ---
try:
    # Cliente ElevenLabs
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"])
    
    # Cliente AWS Bedrock
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-1', 
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY"],
        aws_secret_access_key=st.secrets["AWS_SECRET_KEY"]
    )
except Exception as e:
    st.error(f"Erro na inicialização: Verifique os Secrets (AWS e ElevenLabs).")
    st.stop()

# --- FUNÇÕES CORE ---

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
    """Chama o Claude 3.5 no Amazon Bedrock para gerar a resposta"""
    try:
        prompt_sistema = "Você é o AVI, o assistente virtual de pós-venda da Claro. Seja cordial, direto e resolutivo. Use no máximo 3 frases por resposta."
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "system": prompt_sistema,
            "messages": [{"role": "user", "content": pergunta}]
        })

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=body
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except Exception as e:
        return f"Desculpe, tive um problema ao processar sua solicitação no Bedrock: {e}"

# --- INTERFACE DO USUÁRIO ---
st.title("📞 AVI - Assistente Virtual Claro")
st.subheader("Showcase Pós-Venda - Amazon Bedrock + ElevenLabs")

st.markdown("---")
pergunta = st.text_input("Como posso ajudar você hoje?", placeholder="Ex: Onde está meu iPhone?")

if st.button("Iniciar Chamada"):
    if pergunta:
        with st.spinner("Consultando sistemas Claro via Bedrock..."):
            resposta = obter_resposta_ia(pergunta)
            st.chat_message("assistant").write(resposta)
            tocar_audio(resposta)
    else:
        st.warning("Por favor, digite sua dúvida antes de iniciar.")