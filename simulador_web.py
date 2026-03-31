import streamlit as st
from anthropic import Anthropic
from gtts import gTTS
import os
import base64
from contexto import FAQ_CLARO

# Configurações de página
st.set_page_config(page_title="Simulador Voice IA Claro", page_icon="🔴")

# Título e Branding
st.image("https://upload.wikimedia.org/wikipedia/commons/e/e4/Claro_logo.svg", width=100)
st.title("📞 Simulador 0800 Pós-Venda")
st.markdown("---")

# Função para converter texto em áudio para o navegador
def dar_voz(texto):
    tts = gTTS(text=texto, lang='pt', tld='com.br')
    tts.save("resposta.mp3")
    with open("resposta.mp3", "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# Lógica da IA
client = Anthropic(api_key="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")

def obter_resposta_ia(pergunta):
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=500,
        system=FAQ_CLARO + "\nResponda de forma humanizada e cordial.",
        messages=[{"role": "user", "content": pergunta}]
    )
    return message.content[0].text

# Interface
st.write("👋 **Olá! Sou a assistente virtual do AVI.**")
st.write("Como posso ajudar com seu pedido ou instalação hoje?")

user_input = st.text_input("Digite sua dúvida (simulando a fala):")

if st.button("Enviar"):
    if user_input:
        with st.spinner('Processando...'):
            resposta = obter_resposta_ia(user_input)
            st.info(f"**IA RESPONDE:** {resposta}")
            dar_voz(resposta) # Faz o navegador dela falar!
    else:
        st.warning("Por favor, digite uma pergunta.")