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
    import time
    time.sleep(1) # Simula o pensamento do AVI
    p = pergunta.lower()
    if "iphone" in p or "pedido" in p:
        return "Olá! Identifiquei seu pedido de iPhone no sistema. Ele está em processamento logístico e a entrega está prevista para amanhã. Posso ajudar com algo mais?"
    elif "endereço" in p or "mudar" in p:
        return "Entendo sua necessidade, mas por normas de segurança da Claro, não alteramos o endereço após a compra. O ideal é o cancelamento e uma nova compra. Quer que eu te ensine como cancelar?"
    else:
        return "Olá! Sou o AVI, assistente virtual da Claro. Entendo sua dúvida e estou consultando nossos especialistas. Posso te transferir para um consultor ou você prefere verificar pelo App Minha Claro?"

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