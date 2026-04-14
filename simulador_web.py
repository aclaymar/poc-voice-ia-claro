import streamlit as st
from anthropic import Anthropic
from elevenlabs.client import ElevenLabs
import os
import base64
import time

# 1. ESTA DEVE SER A PRIMEIRA LINHA DO STREAMLIT (Sempre!)
st.set_page_config(page_title="AVI Claro - Pós-Venda", page_icon="📞")

# --- ESTILO CLARO (CSS) ---
st.markdown("""
    <style>
    /* Força o fundo de toda a aplicação para vermelho */
    .stApp {
        background-color: #ee1d23 !important;
    }
    
    /* Garante que os textos, títulos e labels fiquem brancos */
    h1, h2, h3, p, span, label, .stMarkdown {
        color: white !important;
    }

    /* Estiliza o campo de entrada de texto */
    .stTextInput>div>div>input {
        color: black !important; /* Texto que o usuário digita fica preto para leitura */
        border-radius: 10px;
    }

    /* Estiliza o botão para ficar branco com letras vermelhas */
    .stButton>button {
        background-color: white !important;
        color: #ee1d23 !important;
        border-radius: 20px;
        font-weight: bold;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VALIDAÇÃO DE INICIALIZAÇÃO ---
# Se as chaves não existirem, o Streamlit avisará aqui
try:
    client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"])
except Exception as e:
    st.error(f"Erro nas Chaves de API: Verifique os Secrets no painel do Streamlit Cloud.")
    st.stop()

# --- FUNÇÕES CORE ---

def tocar_audio(texto):
    try:
        # Usando o modelo Turbo v2.5: Mais rápido e eficiente para o Showcase
        audio = client_eleven.text_to_speech.convert(
            text=texto,
            voice_id="RGymW84CSmfVugnA5tvA", 
            model_id="eleven_turbo_v2_5" 
        )
        
        audio_bytes = b"".join(audio)
        b64 = base64.b64encode(audio_bytes).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        # Se a ElevenLabs ainda der erro de cota, o app avisa, mas não trava o visual
        st.error(f"Erro ElevenLabs: {e}")

def obter_resposta_ia(pergunta):
    time.sleep(1.0) 
    p = pergunta.lower()
    if "iphone" in p or "pedido" in p or "onde está" in p:
        return "Olá! Com certeza, entendo sua ansiedade. Identifiquei seu pedido de iPhone no sistema. Ele já foi faturado e está em processamento logístico. A entrega está prevista para amanhã até às 18h. Você receberá o código de rastreio por e-mail em breve. Posso ajudar com algo mais?"
    elif "instalação" in p or "técnico" in p or "visita" in p:
        return "Olá, tudo bem? Você pode consultar o horário exato ou até reagendar sua visita técnica direto pelo App Minha Claro Residencial, na seção 'Minhas Visitas'. É muito mais rápido por lá! Deseja que eu envie o link do App para o seu celular?"
    elif "endereço" in p or "mudar" in p:
        return "Entendo sua necessidade, mas por normas de segurança da Claro, não conseguimos alterar o endereço de entrega após o pedido ser gerado. O procedimento padrão é o cancelamento e uma nova compra com o endereço correto. Gostaria que eu te explicasse como fazer o cancelamento?"
    else:
        return "Olá! Sou o AVI, assistente virtual da Claro. Entendo perfeitamente sua dúvida e estou consultando nossas bases de conhecimento. Como prefere seguir?"
    
    # --- INTERFACE DO USUÁRIO ---
st.title("📞 AVI - Assistente Virtual Claro")
st.subheader("Showcase Pós-Venda - Voz Ultra-Realista")

st.markdown("---")
pergunta = st.text_input("Como posso ajudar você hoje?", placeholder="Ex: Onde está meu iPhone?")

if st.button("Iniciar Chamada"):
    if pergunta:
        with st.spinner("Conectando ao AVI..."):
            resposta = obter_resposta_ia(pergunta)
            st.chat_message("assistant").write(resposta)
            tocar_audio(resposta)
    else:
        st.warning("Por favor, digite sua dúvida antes de iniciar.")