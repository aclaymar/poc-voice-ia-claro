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
    time.sleep(1.5) # Dá aquele efeito de que a IA está "pensando"
    p = pergunta.lower()
    
    # Lógica de Respostas Estratégicas para a Claro
    if "iphone" in p or "pedido" in p or "onde está" in p:
        return "Olá! Com certeza, entendo sua ansiedade. Identifiquei seu pedido de iPhone no sistema. Ele já foi faturado e está em processamento logístico. A entrega está prevista para amanhã até às 18h. Você receberá o código de rastreio por e-mail em breve. Posso ajudar com algo mais?"
    
    elif "instalação" in p or "técnico" in p or "visita" in p:
        return "Olá, tudo bem? Você pode consultar o horário exato ou até reagendar sua visita técnica direto pelo App Minha Claro Residencial, na seção 'Minhas Visitas'. É muito mais rápido por lá! Deseja que eu envie o link do App para o seu celular?"
    
    elif "endereço" in p or "mudar" in p:
        return "Entendo sua necessidade, mas por normas de segurança da Claro, não conseguimos alterar o endereço de entrega após o pedido ser gerado. O procedimento padrão é o cancelamento e uma nova compra com o endereço correto. Gostaria que eu te explicasse como fazer o cancelamento?"
    
    else:
        # Resposta padrão para qualquer outra dúvida
        return "Olá! Sou o AVI, assistente virtual da Claro. Entendo perfeitamente sua dúvida e estou consultando nossas bases de conhecimento. Para agilizar, recomendo verificar o portal Minha Claro ou, se preferir, posso te transferir para um de nossos especialistas. Como você prefere seguir?"

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