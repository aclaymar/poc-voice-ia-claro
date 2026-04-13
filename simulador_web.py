import streamlit as st
from anthropic import Anthropic
from elevenlabs.client import ElevenLabs # alterado de gTTs para ElevenLabs
import os
import base64
import time

# 1. Configuração das APIs (Lembrando de adicionar ELEVEN_API_KEY nos Secrets do Streamlit)
client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"]) # Nova API

# 2. Função para falar (Agora com ElevenLabs - Voz Profissional)
def tocar_audio(texto):
    # Gera o áudio usando a voz específica que você escolheu
    audio = client_eleven.generate(
        text=texto,
        voice="RGymW84CSmfVugnA5tvA", # O ID da voz que você compartilhou
        model="eleven_multilingual_v2"
    )
    
    # Converte o gerador de áudio em bytes
    audio_bytes = b"".join(audio)
    
    # Transforma em base64 para o Streamlit tocar sem precisar salvar arquivo local
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

# 3. Função de Resposta (Mantendo a Opção B - Estável para o Showcase)
def obter_resposta_ia(pergunta):
    time.sleep(1.5) 
    p = pergunta.lower()
    
    if "iphone" in p or "pedido" in p or "onde está" in p:
        return "Olá! Com certeza, entendo sua ansiedade. Identifiquei seu pedido de iPhone no sistema. Ele já foi faturado e está em processamento logístico. A entrega está prevista para amanhã até às 18h. Você receberá o código de rastreio por e-mail em breve. Posso ajudar com algo mais?"
    
    elif "instalação" in p or "técnico" in p or "visita" in p:
        return "Olá, tudo bem? Você pode consultar o horário exato ou até reagendar sua visita técnica direto pelo App Minha Claro Residencial, na seção 'Minhas Visitas'. É muito mais rápido por lá! Deseja que eu envie o link do App para o seu celular?"
    
    elif "endereço" in p or "mudar" in p:
        return "Entendo sua necessidade, mas por normas de segurança da Claro, não conseguimos alterar o endereço de entrega após o pedido ser gerado. O procedimento padrão é o cancelamento e uma nova compra com o endereço correto. Gostaria que eu te explicasse como fazer o cancelamento?"
    
    else:
        return "Olá! Sou o AVI, assistente virtual da Claro. Entendo perfeitamente sua dúvida e estou consultando nossas bases de conhecimento. Para agilizar, recomendo verificar o portal Minha Claro ou, se preferir, posso te transferir para um de nossos especialistas. Como você prefere seguir?"

#