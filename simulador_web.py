import streamlit as st
import boto3
import json
from elevenlabs.client import ElevenLabs
import os
import base64
import time
import requests
from streamlit_mic_recorder import mic_recorder
from contexto import SYSTEM_PROMPT, SAUDACAO_INICIAL, RESPOSTA_TRANSFERENCIA, NOME_ASSISTENTE
from guardrails import classificar_input, deve_transferir_humano, sanitizar_resposta
from portfolio import buscar_ofertas, resumo_para_contexto

# ─────────────────────────────────────────────────────
# CONFIGURAÇÃO INICIAL
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{NOME_ASSISTENTE} - Assistente Virtual Claro",
    page_icon="📞",
    layout="centered",
)

# ─────────────────────────────────────────────────────
# ESTILOS CLARO (CSS)
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #ee1d23 !important; }
    h1, h2, h3, p, span, label, .stMarkdown { color: white !important; }
    .stTextInput>div>div>input { color: black !important; border-radius: 10px; }
    .stButton>button {
        background-color: white !important;
        color: #ee1d23 !important;
        border-radius: 20px;
        font-weight: bold;
    }
    .status-falando {
        background: rgba(255,255,255,0.15);
        border-radius: 12px;
        padding: 8px 16px;
        text-align: center;
        animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
        0%   { opacity: 1; }
        50%  { opacity: 0.4; }
        100% { opacity: 1; }
    }
    .chat-user {
        background: rgba(255,255,255,0.2);
        border-radius: 12px;
        padding: 10px 14px;
        margin: 6px 0;
        text-align: right;
    }
    .chat-clarinha {
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 10px 14px;
        margin: 6px 0;
    }
    .badge-transferencia {
        background: #ffd700;
        color: #333 !important;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 0.85em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# JAVASCRIPT: SOM AMBIENTE DE CALL CENTER + INTERRUPÇÃO
# ─────────────────────────────────────────────────────
st.markdown("""
<script>
// ── SOM AMBIENTE DE CALL CENTER (Web Audio API) ──────────────────
(function() {
    let ambientCtx = null;
    let ambientGain = null;
    let ambientRunning = false;

    function criarSomAmbiente() {
        if (ambientRunning) return;
        try {
            ambientCtx = new (window.AudioContext || window.webkitAudioContext)();
            ambientGain = ambientCtx.createGain();
            ambientGain.gain.value = 0.04; // volume muito baixo — fundo discreto
            ambientGain.connect(ambientCtx.destination);

            // Pink noise buffer (ruído de escritório)
            const bufferSize = ambientCtx.sampleRate * 2;
            const buffer = ambientCtx.createBuffer(1, bufferSize, ambientCtx.sampleRate);
            const data = buffer.getChannelData(0);
            let b0=0, b1=0, b2=0, b3=0, b4=0, b5=0, b6=0;
            for (let i = 0; i < bufferSize; i++) {
                const white = Math.random() * 2 - 1;
                b0 = 0.99886*b0 + white*0.0555179;
                b1 = 0.99332*b1 + white*0.0750759;
                b2 = 0.96900*b2 + white*0.1538520;
                b3 = 0.86650*b3 + white*0.3104856;
                b4 = 0.55000*b4 + white*0.5329522;
                b5 = -0.7616*b5 - white*0.0168980;
                data[i] = (b0+b1+b2+b3+b4+b5+b6 + white*0.5362) / 7;
                b6 = white * 0.115926;
            }

            const source = ambientCtx.createBufferSource();
            source.buffer = buffer;
            source.loop = true;
            source.connect(ambientGain);
            source.start();
            ambientRunning = true;
            console.log("[Clarinha] Som ambiente ativado.");
        } catch(e) {
            console.log("[Clarinha] Web Audio não disponível:", e);
        }
    }

    function pararSomAmbiente() {
        if (ambientCtx) {
            ambientCtx.close();
            ambientRunning = false;
        }
    }

    // Ativa som ao primeiro clique/toque (política de autoplay)
    window._clarinha_iniciarAmbiente = criarSomAmbiente;
    window._clarinha_pararAmbiente = pararSomAmbiente;

    document.addEventListener('click', function iniciar() {
        criarSomAmbiente();
        document.removeEventListener('click', iniciar);
    }, { once: true });
})();

// ── CONTROLE DE ÁUDIO TTS + INTERRUPÇÃO ──────────────────────────
window._clarinaAudioAtual = null;
window._clarinhaParlando = false;

window._clarinha_parar_audio = function() {
    if (window._clarinaAudioAtual) {
        window._clarinaAudioAtual.pause();
        window._clarinaAudioAtual.currentTime = 0;
        window._clarinaAudioAtual = null;
    }
    window._clarinhaParlando = false;
    const status = document.getElementById('status-clarinha');
    if (status) status.style.display = 'none';
};

// Detecta quando o microfone começa a gravar e para o áudio atual
const _origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
navigator.mediaDevices.getUserMedia = async function(constraints) {
    if (constraints && constraints.audio) {
        window._clarinha_parar_audio();
    }
    return _origGetUserMedia(constraints);
};
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# INICIALIZAÇÃO DE APIS E CLIENTES AWS
# ─────────────────────────────────────────────────────
try:
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"])

    aws_auth = {
        "aws_access_key_id":     st.secrets["AWS_ACCESS_KEY"],
        "aws_secret_access_key": st.secrets["AWS_SECRET_KEY"],
        "region_name":           "us-east-1",
    }
    bedrock          = boto3.client(service_name="bedrock-runtime", **aws_auth)
    s3_client        = boto3.client("s3",         **aws_auth)
    transcribe_client = boto3.client("transcribe", **aws_auth)

except Exception:
    st.error("Erro na inicialização: verifique os Secrets configurados.")
    st.stop()

# ─────────────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────────────
if "historico" not in st.session_state:
    st.session_state.historico = []
if "saudacao_feita" not in st.session_state:
    st.session_state.saudacao_feita = False
if "som_ambiente" not in st.session_state:
    st.session_state.som_ambiente = True
if "perfil_cliente" not in st.session_state:
    st.session_state.perfil_cliente = "prospect"

# ─────────────────────────────────────────────────────
# FUNÇÕES CORE
# ─────────────────────────────────────────────────────

def transcrever_audio_aws(audio_bytes: bytes) -> str | None:
    """Sobe o áudio para S3 e transcreve via Amazon Transcribe (pt-BR)."""
    job_name  = f"clarinha_{int(time.time())}"
    bucket    = "audio-claro-poc-andy"
    file_key  = f"{job_name}.webm"

    try:
        s3_client.put_object(Bucket=bucket, Key=file_key, Body=audio_bytes)

        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"s3://{bucket}/{file_key}"},
            MediaFormat="webm",
            LanguageCode="pt-BR",
        )

        for _ in range(120):  # timeout: 120 segundos
            status = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )["TranscriptionJob"]["TranscriptionJobStatus"]
            if status == "COMPLETED":
                break
            if status == "FAILED":
                return None
            time.sleep(1)

        result_url = transcribe_client.get_transcription_job(
            TranscriptionJobName=job_name
        )["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        return requests.get(result_url).json()["results"]["transcripts"][0]["transcript"]

    except Exception as e:
        st.error(f"Erro no Amazon Transcribe: {e}")
        return None


def tocar_audio(texto: str, autoplay: bool = True):
    """
    Converte texto para fala via ElevenLabs e injeta o player com controles
    de interrupção. O áudio é interrompido automaticamente se o microfone
    for ativado (via JS interceptor em getUserMedia).
    """
    try:
        audio_chunks = client_eleven.text_to_speech.convert(
            text=texto,
            voice_id="RGymW84CSmfVugnA5tvA",
            model_id="eleven_turbo_v2_5",
            voice_settings={
                "stability":        0.50,
                "similarity_boost": 0.85,
                "style":            0.30,
                "use_speaker_boost": True,
            },
        )
        audio_bytes = b"".join(audio_chunks)
        b64 = base64.b64encode(audio_bytes).decode()

        autoplay_attr = 'autoplay="true"' if autoplay else ""
        st.markdown(
            f"""
            <div id="status-clarinha" class="status-falando">
                🎙️ {NOME_ASSISTENTE} está falando...
                <button onclick="window._clarinha_parar_audio()"
                        style="margin-left:12px; padding:4px 12px;
                               border-radius:8px; border:none;
                               background:white; color:#ee1d23;
                               font-weight:bold; cursor:pointer;">
                    ⏹ Parar
                </button>
            </div>
            <audio id="audio-clarinha" {autoplay_attr}
                   onended="document.getElementById('status-clarinha').style.display='none';
                            window._clarinhaParlando=false;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                (function() {{
                    var a = document.getElementById('audio-clarinha');
                    window._clarinaAudioAtual = a;
                    window._clarinhaParlando = true;
                    window._clarinha_iniciarAmbiente && window._clarinha_iniciarAmbiente();
                }})();
            </script>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.error(f"Erro no ElevenLabs: {e}")


def _montar_historico_bedrock() -> list:
    """Converte o histórico da sessão para o formato messages do Bedrock."""
    msgs = []
    for turno in st.session_state.historico:
        msgs.append({"role": "user",      "content": turno["usuario"]})
        msgs.append({"role": "assistant", "content": turno["clarinha"]})
    return msgs


def obter_resposta_ia(pergunta: str) -> tuple[str, bool]:
    """
    Envia a pergunta ao LLM (Bedrock / Claude) com:
      - Guardrails em camada (classificação prévia)
      - System prompt completo (identidade + FAQ + regras)
      - Histórico de conversa
      - Contexto de portfólio residencial (quando relevante)

    Retorna: (resposta_texto, precisa_transferir)
    """
    # ── Guardrail de entrada ───────────────────────────
    avaliacao = classificar_input(pergunta)
    if avaliacao["resposta_guardrail"]:
        return avaliacao["resposta_guardrail"], False

    # ── Contexto dinâmico de portfólio ─────────────────
    contexto_extra = ""
    palavras_residencial = [
        "internet", "fibra", "tv", "residencial", "instalação",
        "net virtua", "combo", "gpon", "velocidade", "mega",
    ]
    if any(p in pergunta.lower() for p in palavras_residencial):
        contexto_extra = (
            "\n\n--- CONTEXTO PORTFÓLIO RESIDENCIAL ---\n"
            + resumo_para_contexto(st.session_state.perfil_cliente)
        )

    # ── Chamada ao Bedrock ─────────────────────────────
    try:
        historico = _montar_historico_bedrock()
        historico.append({"role": "user", "content": pergunta})

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens":        600,
            "system":            SYSTEM_PROMPT + contexto_extra,
            "messages":          historico,
        })
        response      = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=body,
        )
        response_body = json.loads(response["body"].read())
        resposta      = response_body["content"][0]["text"]

    except Exception as e:
        # Fallback local com respostas humanizadas
        resposta = _resposta_fallback(pergunta)

    # ── Sanitização e verificação de transferência ─────
    resposta = sanitizar_resposta(resposta)
    precisa_transferir = deve_transferir_humano(resposta)

    return resposta, precisa_transferir


def _resposta_fallback(pergunta: str) -> str:
    """Respostas humanizadas de contingência quando o LLM não está disponível."""
    p = pergunta.lower()
    if any(w in p for w in ["endereço", "endereco"]):
        return (
            "Entendo sua necessidade! Por segurança, não é possível alterar o endereço "
            "após o pedido ser gerado. Posso te orientar sobre o cancelamento e um novo pedido."
        )
    if any(w in p for w in ["instalação", "instalacao", "técnico", "tecnico"]):
        return (
            "Você pode consultar ou reagendar sua visita técnica pelo app Minha Claro "
            "Residencial, em Minhas Visitas. É bem rápido! Posso te ajudar com mais alguma coisa?"
        )
    if any(w in p for w in ["chip", "esim", "e-sim", "portabilidade"]):
        return (
            "A ativação do chip ou eSIM leva até 48 horas. Após a ativação, "
            "você pode solicitar a portabilidade pelo app Minha Claro ou ligando para o 1052."
        )
    if any(w in p for w in ["fatura", "boleto", "pagamento", "cobrança"]):
        return (
            "Você pode consultar sua fatura pelo app Minha Claro ou pelo site claro.com.br. "
            "Se precisar de ajuda com um valor, posso te conectar com nosso time financeiro."
        )
    return (
        "Estou aqui para te ajudar! Seu pedido está seguindo o fluxo normal e "
        "você receberá atualizações por e-mail. Posso te ajudar com mais alguma coisa?"
    )


# ─────────────────────────────────────────────────────
# INTERFACE DO USUÁRIO
# ─────────────────────────────────────────────────────
st.title(f"📞 {NOME_ASSISTENTE} — Assistente Virtual Claro")
st.caption("Atendimento inteligente · Powered by Claro + AWS + ElevenLabs")
st.markdown("---")

# Controles laterais
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Claro_logo.svg/320px-Claro_logo.svg.png",
        width=140,
    )
    st.markdown("### Configurações")
    st.session_state.perfil_cliente = st.selectbox(
        "Perfil do cliente",
        ["prospect", "base"],
        help="prospect = novo cliente | base = já é cliente Claro",
    )
    st.session_state.som_ambiente = st.toggle(
        "Som ambiente call center", value=st.session_state.som_ambiente
    )
    st.markdown("---")
    st.markdown("**Canais de suporte:**")
    st.markdown("📱 App Minha Claro")
    st.markdown("📞 Móvel: 1052")
    st.markdown("🏠 Residencial: 0800 383 2121")
    st.markdown("🛒 E-commerce: 0800 738 0001")
    if st.button("🔄 Nova Conversa"):
        st.session_state.historico = []
        st.session_state.saudacao_feita = False
        st.rerun()

# ── Saudação inicial (uma vez por sessão) ─────────────
if not st.session_state.saudacao_feita:
    with st.container():
        st.markdown(
            f'<div class="chat-clarinha">🤖 <b>{NOME_ASSISTENTE}:</b> {SAUDACAO_INICIAL}</div>',
            unsafe_allow_html=True,
        )
        tocar_audio(SAUDACAO_INICIAL, autoplay=True)
    st.session_state.saudacao_feita = True

# ── Histórico de conversa ──────────────────────────────
for turno in st.session_state.historico:
    st.markdown(
        f'<div class="chat-user">👤 <b>Você:</b> {turno["usuario"]}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="chat-clarinha">🤖 <b>{NOME_ASSISTENTE}:</b> {turno["clarinha"]}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Input por voz ──────────────────────────────────────
st.markdown("### 🎙️ Fale com a Clarinha")
st.caption("Clique em 'Iniciar' — ela para automaticamente quando você começar a falar.")

audio_gravado = mic_recorder(
    start_prompt="🔴 Iniciar Conversa por Voz",
    stop_prompt="🟢 Enviar Áudio",
    key="recorder",
)

# ── Input por texto ────────────────────────────────────
st.markdown("### ⌨️ Ou digite sua dúvida")
col1, col2 = st.columns([5, 1])
with col1:
    pergunta_texto = st.text_input(
        "Como posso ajudar?",
        placeholder="Ex: Quais planos de internet tem disponível?",
        label_visibility="collapsed",
    )
with col2:
    enviar_btn = st.button("Enviar", use_container_width=True)

# ── Processamento ──────────────────────────────────────
pergunta_final = None

if audio_gravado:
    with st.spinner("🎧 Transcrevendo seu áudio..."):
        pergunta_final = transcrever_audio_aws(audio_gravado["bytes"])
        if pergunta_final:
            st.success(f"🗣️ Você disse: **{pergunta_final}**")
        else:
            st.warning("Não consegui entender o áudio. Tente novamente ou use o texto.")

elif enviar_btn and pergunta_texto.strip():
    pergunta_final = pergunta_texto.strip()

if pergunta_final:
    with st.spinner(f"💭 {NOME_ASSISTENTE} está pensando..."):
        resposta, precisa_transferir = obter_resposta_ia(pergunta_final)

    # Exibe a conversa
    st.markdown(
        f'<div class="chat-user">👤 <b>Você:</b> {pergunta_final}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="chat-clarinha">🤖 <b>{NOME_ASSISTENTE}:</b> {resposta}</div>',
        unsafe_allow_html=True,
    )

    # Badge de transferência
    if precisa_transferir:
        st.markdown(
            '<div class="badge-transferencia">⚡ Transferindo para especialista humano...</div>',
            unsafe_allow_html=True,
        )
        tocar_audio(RESPOSTA_TRANSFERENCIA, autoplay=True)
    else:
        tocar_audio(resposta, autoplay=True)

    # Salva no histórico
    st.session_state.historico.append({
        "usuario":  pergunta_final,
        "clarinha": resposta,
    })
