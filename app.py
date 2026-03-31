import os
import pyttsx3
from dotenv import load_dotenv
from anthropic import Anthropic
from contexto import FAQ_CLARO

# 1. Configurações de Segurança
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Plano B: Caso o .env falhe, cole sua chave aqui
if not api_key or "sk-ant" not in api_key:
    api_key = "REMOVED_SEE_ENV"

try:
    client = Anthropic(api_key=api_key.strip())
except Exception as e:
    print(f"Erro ao iniciar cliente: {e}")

# 2. Motor de Voz (TTS)
def falar(texto):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 185) 
        voices = engine.getProperty('voices')
        for voice in voices:
            if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.say(texto)
        engine.runAndWait()
    except Exception as e:
        print(f"Erro no áudio: {e}")

# 3. Lógica Dinâmica e Humanizada
def simular_atendimento_claro(pergunta_usuario):
    try:
        # Aqui o Claude usa as FAQs para criar a resposta na hora
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=500,
            system=FAQ_CLARO + """
            INSTRUÇÕES ADICIONAIS:
            - Seja sempre cordial, empático e humanizado.
            - Use expressões como 'Com certeza', 'Entendo sua dúvida' ou 'Um momento, por favor'.
            - Se a dúvida for sobre status de pedido, lembre-se que temos alto volume (~9.200 chamadas/mês). [cite: 9, 46, 163]
            - Seja objetivo para manter o TMO próximo dos 304 segundos. [cite: 46, 148]
            """, 
            messages=[{"role": "user", "content": pergunta_usuario}]
        )
        return message.content[0].text
    except Exception:
        # Resposta humanizada de contingência baseada nas FAQs
        p = pergunta_usuario.lower()
        if "endereço" in p:
            return "Olá! Entendo sua necessidade, mas por segurança não conseguimos mudar o endereço após o pedido gerado. O ideal é cancelar e refazer a compra. Posso te ajudar com o passo a passo?"
        if "instalação" in p or "técnico" in p:
            return "Olá, tudo bem? Você pode consultar ou reagendar sua visita técnica direto pelo App Minha Claro Residencial. É super rápido! Deseja saber mais algum detalhe?"
        return "Com certeza! Identifiquei seu pedido e ele está seguindo o fluxo normal. Você receberá o status atualizado por e-mail em até 24 horas. Posso ajudar em algo mais?"

# 4. Interface de Teste
if __name__ == "__main__":
    # Simulação de início de chamada
    inicio_chamada = "Olá! Você ligou para o Pós-Venda da Claro. Sou a assistente virtual do AVI. Como posso te ajudar hoje?"
    
    print("\n--- [CHAMADA INICIADA: 0800 CLARO] ---")
    print(f"\n[IA]: {inicio_chamada}")
    falar(inicio_chamada) # Ela já começa falando!

    # Agora você interage
    pergunta = input("\n[VOCÊ]: ")
    
    print("\n[IA PROCESSANDO...]")
    resposta = simular_atendimento_claro(pergunta)
    
    print(f"\n[IA RESPONDE]: {resposta}")
    falar(resposta)