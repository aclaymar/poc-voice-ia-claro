import streamlit as st
from anthropic import Anthropic
from gtts import gTTS
import os
import base64
import time

# 1. Configuração da API (Use sua chave sk-ant aqui para o teste no PyCharm)
client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
# 2. Função para falar (Voz da Claro)
def tocar_audio(texto):
    tts = gTTS(text=texto, lang='pt', tld='com.br')
    tts.save("resposta.mp3")
    with open("resposta.mp3", "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)
    os.remove("resposta.mp3")

# 3. Função que CHAMA a Inteligência Real (Claude 3.5)
def obter_resposta_ia(pergunta):
    try:
        # Aqui ele vai usar o saldo de $5 para pensar de verdade
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            system="Você é o AVI, assistente virtual da Claro. Use as FAQs de Pós-Venda para responder de forma empática e curta.",
            messages=[{"role": "user", "content": pergunta}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Erro de conexão: {e}"

# 4. Interface Visual (O que a Dri vai ver)
st.set_page_config(page_title="Simulador AVI Claro", page_icon="📞")

st.markdown("<h1 style='text-align: center; color: #ee1111;'>📞 Simulador 0800 Claro</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Atendimento Especializado Pós-Venda</h3>", unsafe_allow_html=True)

canal = st.sidebar.selectbox("Canal:", ["BCC / CSU", "Retenção", "Vendas"])
motor = st.sidebar.info("Motor IA: Claude 3.5 Sonnet")

user_input = st.text_input("Simule sua fala (Cliente):", placeholder="Ex: Onde está meu pedido?")

if st.button("Iniciar Chamada", type="primary"):
    if user_input:
        with st.spinner('AVI processando...'):
            resposta = obter_resposta_ia(user_input)
            st.write(f"**AVI:** {resposta}")
            tocar_audio(resposta)
    else:
        st.warning("Por favor, digite uma dúvida para iniciar.")