import os
import pyttsx3
from dotenv import load_dotenv
from anthropic import Anthropic
from contexto import SYSTEM_PROMPT, SAUDACAO_INICIAL, RESPOSTA_TRANSFERENCIA, NOME_ASSISTENTE
from guardrails import classificar_input, deve_transferir_humano, sanitizar_resposta

load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print(f"\n[ERRO]: Variável ANTHROPIC_API_KEY não encontrada!")
    print("Certifique-se de que o arquivo .env existe ou a variável está configurada.")

try:
    client = Anthropic(api_key=api_key.strip() if api_key else "")
except Exception as e:
    print(f"Erro ao iniciar cliente Anthropic: {e}")

historico: list[dict] = []


def falar(texto: str):
    """TTS local via pyttsx3 (fallback para testes sem ElevenLabs)."""
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        for voice in engine.getProperty("voices"):
            if any(k in voice.name.lower() for k in ["brazil", "portuguese", "brasil"]):
                engine.setProperty("voice", voice.id)
                break
        engine.say(texto)
        engine.runAndWait()
    except Exception as e:
        print(f"[ERRO TTS]: {e}")


def responder(pergunta: str) -> tuple[str, bool]:
    """
    Processa a pergunta com guardrails e LLM.
    Retorna (resposta, precisa_transferir_humano).
    """
    # Guardrail de entrada
    avaliacao = classificar_input(pergunta)
    if avaliacao["resposta_guardrail"]:
        return avaliacao["resposta_guardrail"], False

    # Monta histórico para contexto multi-turno
    msgs = []
    for turno in historico:
        msgs.append({"role": "user",      "content": turno["usuario"]})
        msgs.append({"role": "assistant", "content": turno["clarinha"]})
    msgs.append({"role": "user", "content": pergunta})

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=msgs,
        )
        resposta = message.content[0].text

    except Exception:
        # Fallback humanizado
        p = pergunta.lower()
        if any(w in p for w in ["endereço", "endereco"]):
            resposta = (
                "Entendo sua necessidade! Por segurança, não é possível alterar "
                "o endereço após o pedido ser gerado. Posso orientar sobre o cancelamento."
            )
        elif any(w in p for w in ["instalação", "técnico"]):
            resposta = (
                "Você pode reagendar sua visita técnica pelo app Minha Claro Residencial, "
                "em Minhas Visitas. Posso ajudar com mais alguma coisa?"
            )
        else:
            resposta = (
                "Estou aqui para te ajudar! Pode me contar mais sobre sua dúvida?"
            )

    resposta = sanitizar_resposta(resposta)
    precisa_transferir = deve_transferir_humano(resposta)
    return resposta, precisa_transferir


def main():
    print(f"\n{'─'*50}")
    print(f"   {NOME_ASSISTENTE.upper()} — ASSISTENTE VIRTUAL CLARO")
    print(f"{'─'*50}")
    print("[CHAMADA INICIADA: 0800 CLARO]\n")
    print(f"[{NOME_ASSISTENTE}]: {SAUDACAO_INICIAL}")
    falar(SAUDACAO_INICIAL)

    while True:
        try:
            pergunta = input("\n[VOCÊ]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n[{NOME_ASSISTENTE}]: Obrigada por entrar em contato com a Claro. Até logo!")
            break

        if not pergunta:
            continue

        if pergunta.lower() in ["sair", "tchau", "encerrar", "exit"]:
            encerramento = "Obrigada por entrar em contato com a Claro. Tenha um ótimo dia!"
            print(f"\n[{NOME_ASSISTENTE}]: {encerramento}")
            falar(encerramento)
            break

        print(f"\n[{NOME_ASSISTENTE} processando...]")
        resposta, precisa_transferir = responder(pergunta)

        print(f"\n[{NOME_ASSISTENTE}]: {resposta}")
        falar(resposta)

        if precisa_transferir:
            print(f"\n[SISTEMA]: Transferindo para especialista humano...")
            print(f"[{NOME_ASSISTENTE}]: {RESPOSTA_TRANSFERENCIA}")
            falar(RESPOSTA_TRANSFERENCIA)
            break

        historico.append({"usuario": pergunta, "clarinha": resposta})


if __name__ == "__main__":
    main()
