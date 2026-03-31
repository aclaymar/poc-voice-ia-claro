from openai import OpenAI  # Importe a OpenAI
import streamlit as st
# ... (mantenha os outros imports)

# Substitua a criação do cliente
client = OpenAI(api_key="SUA_CHAVE_OPENAI_AQUI")

def obter_resposta_ia(pergunta):
    response = client.chat.completions.create(
        model="gpt-4o", # Ou gpt-3.5-turbo se quiser economizar
        messages=[
            {"role": "system", "content": FAQ_CLARO + "\nSeja cordial, empático e humanizado como o AVI da Claro."},
            {"role": "user", "content": pergunta}
        ]
    )
    return response.choices[0].message.content