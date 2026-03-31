import os
import pyttsx3
from dotenv import load_dotenv
from anthropic import Anthropic

# 1. Configurações Iniciais e Segurança
load_dotenv()
# O .strip() garante que não haja espaços invisíveis na sua chave sk-ant-...
api_key = os.environ.get("ANTHROPIC_API_KEY").strip()
client = Anthropic(api_key=api_key)

# 2. Função de Voz (TTS)
def falar(texto):
    engine = pyttsx3.init()
    # Ajuste de velocidade (180-200 é um tom humano natural)
    engine.setProperty('rate', 185) 
    
    # Tenta selecionar uma voz em Português instalada no seu Windows
    voices = engine.getProperty('voices')
    for voice in voices:
        if "brazil" in voice.name.lower() or "portuguese" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
            
    engine.say(texto)
    engine.runAndWait()

# 3. Função de Inteligência (Claude 3.5 Sonnet)
def simular_atendimento_claro(pergunta_usuario):
    prompt_sistema = """
    Você é a assistente de voz do Pós-Venda de E-commerce da Claro.
    Seu objetivo é reduzir o TMO (atualmente 304s) sendo resolutiva.
    
    DADOS DE NEGÓCIO (Baseado nos relatórios BCC/CSU):
    - Status de Pedido: ~9.200 chamadas/mês (Maior volume).
    - Cancelamento: ~4.900 chamadas/mês.
    - Se for sobre iPhone/Entrega: Informe que o prazo de processamento é de 24h para o e-mail.
    
    ESTILO DE RESPOSTA:
    - Respostas curtas (máximo 3 frases).
    - Tom de voz profissional, empático e moderno.
    - Não use listas ou caracteres especiais, apenas texto corrido para facilitar a fala.
    """

    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=500,
        system=prompt_sistema,
        messages=[{"role": "user", "content": pergunta_usuario}]
    )
    return message.content[0].text

# 4. Execução da POC
if __name__ == "__main__":
    print("\n--- [PROTOTIPO VOICE IA CLARO ATIVO] ---")
    print("Pós-Venda E-commerce: BCC (Móvel) e CSU (Residencial)")
    
    pergunta = input("\nSimule a fala do cliente: ")
    
    print("\n[IA PROCESSANDO...]")
    resposta = simular_atendimento_claro(pergunta)
    
    print(f"\n[IA RESPONDE]: {resposta}")
    
    # Chama a função para o computador falar
    falar(resposta)