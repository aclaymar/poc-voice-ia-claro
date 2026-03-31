import streamlit as st
from anthropic import Anthropic
import os
from contexto import FAQ_CLARO

# Configuração da Página
st.set_page_config(page_title="Claro Voice IA - Simulator", page_icon="📞")

# Estilização para parecer um celular (CSS Simples)
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #e30613; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("📞 Simulador 0800 Claro")
st.subheader("Atendimento Especializado Pós-Venda")

# Lógica da IA (Mesma que você já tem)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def obter_resposta(pergunta):
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=500,
        system=FAQ_CLARO + " Seja cordial e humanizado.",
        messages=[{"role": "user", "content": pergunta}]
    )
    return message.content[0].text

# Interface do Simulador
col1, col2 = st.columns([1, 2])

with col1:
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e4/Claro_logo.svg", width=100)
    st.write("**Canal:** BCC / CSU")
    st.write("**IA Engine:** Claude 3.5")

with col2:
    user_input = st.text_input("Simule sua fala (Cliente):", placeholder="Ex: Onde está meu pedido?")

    if st.button("Iniciar Chamada"):
        if user_input:
            with st.spinner('Processando Voz...'):
                resposta = obter_resposta(user_input)
                st.info(f"**IA RESPONDE:** {resposta}")
                # Nota: Áudio em navegador requer bibliotecas extras como gTTS ou Streamlit-Audio
                st.audio("https://www.soundjay.com/phone/phone-calling-1.mp3") # Som de telefone
        else:
            st.warning("Por favor, diga algo para começar.")