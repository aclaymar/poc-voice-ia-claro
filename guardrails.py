# guardrails.py - Classificação de Inputs e Proteção da Marca Claro
# Camada de segurança antes de enviar ao LLM

import re

# ──────────────────────────────────────────────
# LISTAS DE DETECÇÃO
# ──────────────────────────────────────────────

_TENTATIVAS_JAILBREAK = [
    r"ignor[ae]\b.*instru",
    r"esqueç[ae]\b.*instru",
    r"nova instru[cç]",
    r"fin[jg][ae]\b.*(ser|que)",
    r"pretend",
    r"roleplay",
    r"como se (fosse|voc[eê] fosse|n[aã]o tivesse)",
    r"voc[eê] agora [eé]",
    r"a partir de agora",
    r"\bDAN\b",
    r"modo desenvolvedor",
    r"sem restri[cç][oõ]es",
    r"sem filtros?",
    r"modo (sem censura|livre|hacker|god)",
    r"bypass",
    r"jailbreak",
    r"act as",
    r"you are now",
    r"override",
    r"prompt injection",
    r"ignore (all|previous|your)",
    r"disregard",
    r"system prompt",
]

_CONCORRENTES = [
    r"\bvivo\b",
    r"\btim\b",
    r"\b(oi|oi\s+telecom)\b",
    r"\bsky\b",
    r"\bnextel\b",
    r"\balgar\b",
    r"\bsercomtel\b",
    r"\bamericatel\b",
    r"\bclaro\s+tv\+\b",  # outra marca
    r"\bclaro\s+sky\b",
]

_FORA_ESCOPO = [
    r"\b(previs[aã]o|clima|tempo)\b.*\b(hoje|amanh[aã]|semana)\b",
    r"\b(receita|ingrediente|prato|culin[aá]ri)\b",
    r"\b(futebol|placar|campeonato|time de)\b",
    r"\b(pol[ií]tic[ao]|presidente|governador|eleic[aã]o|partido)\b",
    r"\b(religi[aã]o|deus|jesus|orac[aã]o|bib[lí]ia)\b",
    r"\b(concurso p[uú]blico|enem|vestibular)\b",
    r"\b(investimento|bolsa de valores|a[cç][aã]o|criptomoeda|bitcoin)\b",
    r"\b(m[eé]dic[ao]|rem[eé]dio|diagn[oó]stico|sintoma|doen[cç]a)\b",
    r"\b(advogad[ao]|processo judicial|lei\s+\d+)\b",
    r"\b(how to|tutorial de|como fazer)\b.*(hack|invasão|crack|piratear)\b",
]

_OFENSIVO = [
    r"\b(palavr[aã]o|xingamento)\b",  # meta
    r"merda|porra|caralho|foda[- ]se|viado|vagabund",
    r"\b(racist[ao]|nazist[ao]|fascist[ao])\b",
    r"matar|suicid|exploit|bomb[ae]",
]


# ──────────────────────────────────────────────
# FUNÇÃO PRINCIPAL DE CLASSIFICAÇÃO
# ──────────────────────────────────────────────

def classificar_input(texto: str) -> dict:
    """
    Classifica o input do usuário antes de enviar ao LLM.

    Retorna um dict com:
      - categoria: "ok" | "jailbreak" | "concorrente" | "fora_escopo" | "ofensivo"
      - score: 0-10 (risco estimado)
      - resposta_guardrail: resposta pronta se categoria != "ok", senão None
    """
    t = texto.lower().strip()

    # 1. Tentativa de jailbreak / manipulação de identidade
    for pattern in _TENTATIVAS_JAILBREAK:
        if re.search(pattern, t, re.IGNORECASE):
            return {
                "categoria": "jailbreak",
                "score": 9,
                "resposta_guardrail": (
                    "Sou a Clarinha, assistente virtual da Claro, e estou aqui para te ajudar "
                    "com tudo sobre os produtos e serviços da Claro. "
                    "Como posso te auxiliar hoje?"
                ),
            }

    # 2. Conteúdo ofensivo
    for pattern in _OFENSIVO:
        if re.search(pattern, t, re.IGNORECASE):
            return {
                "categoria": "ofensivo",
                "score": 8,
                "resposta_guardrail": (
                    "Preciso que nossa conversa seja respeitosa para que eu possa te ajudar bem. "
                    "Posso te auxiliar com qualquer dúvida sobre produtos e serviços da Claro. "
                    "Como posso te ajudar?"
                ),
            }

    # 3. Menção a concorrentes (deixa passar para o LLM com nota, mas com baixo score)
    menciona_concorrente = any(
        re.search(p, t, re.IGNORECASE) for p in _CONCORRENTES
    )

    # 4. Fora do escopo Claro
    for pattern in _FORA_ESCOPO:
        if re.search(pattern, t, re.IGNORECASE):
            return {
                "categoria": "fora_escopo",
                "score": 5,
                "resposta_guardrail": (
                    "Meu foco é te ajudar com tudo sobre a Claro! "
                    "Posso te auxiliar com planos, serviços, pedidos ou dúvidas sobre a Claro. "
                    "Como posso te ajudar?"
                ),
            }

    # 5. Input OK (passa para o LLM)
    return {
        "categoria": "ok",
        "score": 1 if menciona_concorrente else 0,
        "resposta_guardrail": None,
        "menciona_concorrente": menciona_concorrente,
    }


def deve_transferir_humano(resposta_ia: str) -> bool:
    """
    Verifica se a resposta gerada pela IA indica necessidade de transferência humana.
    """
    indicadores = [
        "não consigo resolver",
        "não tenho acesso",
        "precisa de um especialista",
        "vou te transferir",
        "encaminhar para",
        "equipe especializada",
        "cancelamento",
        "rescisão",
        "processo judicial",
        "ouvidoria",
    ]
    resp = resposta_ia.lower()
    return any(ind in resp for ind in indicadores)


def sanitizar_resposta(texto: str) -> str:
    """
    Remove elementos que não funcionam bem em TTS (Text-to-Speech).
    Substitui símbolos, URLs, marcadores por versões faladas.
    """
    # Remove URLs
    texto = re.sub(r"https?://\S+", "", texto)
    # Remove emojis e símbolos
    texto = re.sub(r"[#*_~`|>\\]", "", texto)
    texto = re.sub(r"[\U00010000-\U0010ffff]", "", texto, flags=re.UNICODE)
    # Remove marcadores de lista
    texto = re.sub(r"^\s*[-•·]\s+", "", texto, flags=re.MULTILINE)
    # Normaliza múltiplos espaços
    texto = re.sub(r"\s{2,}", " ", texto)
    # Normaliza múltiplas exclamações/interrogações
    texto = re.sub(r"[!]{2,}", "!", texto)
    texto = re.sub(r"[?]{2,}", "?", texto)
    return texto.strip()
