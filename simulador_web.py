"""
Clarinha — Assistente Virtual de Voz da Claro Brasil
Simulador com UI estilo iPhone
"""
import streamlit as st
import boto3
import json
from elevenlabs.client import ElevenLabs
import base64
import time
import requests
import os
from streamlit_mic_recorder import mic_recorder
from contexto import SYSTEM_PROMPT, SAUDACAO_INICIAL, RESPOSTA_TRANSFERENCIA, NOME_ASSISTENTE
from guardrails import classificar_input, deve_transferir_humano, sanitizar_resposta
from portfolio import resumo_para_contexto

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{NOME_ASSISTENTE} · Claro",
    page_icon="📞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

NUMERO_CLARO   = "0800 738 0001"
CLARINHA_PHOTO = "img/clarinha.png"
HAS_PHOTO      = os.path.exists(CLARINHA_PHOTO)

# Pré-carrega a foto como base64 para funcionar no Streamlit Cloud
# (st.markdown com <img src="path"> não acessa o filesystem do servidor)
_PHOTO_B64 = ""
_PHOTO_URI = ""
if HAS_PHOTO:
    with open(CLARINHA_PHOTO, "rb") as _f:
        _PHOTO_B64 = base64.b64encode(_f.read()).decode()
    _PHOTO_URI = f"data:image/png;base64,{_PHOTO_B64}"

# Modelos Bedrock em ordem de preferência
BEDROCK_MODELS = [
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
]

# ─────────────────────────────────────────────────────
# CSS — SITE COM FRAME DE IPHONE
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fundo da página (mesa/desk) ──────────────────── */
.stApp {
    background: radial-gradient(ellipse at 50% 0%, #1a2040 0%, #090c1e 70%) !important;
    min-height: 100vh;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── Frame externo do iPhone ─────────────────────── */
.block-container {
    max-width: 393px !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 28px auto 28px !important;

    /* Corpo do telefone */
    background: #0d0d0f !important;
    border-radius: 52px !important;

    /* Moldura metálica */
    outline: 10px solid #2a2a2e;
    outline-offset: 0;
    box-shadow:
        0 0 0 1px #111,
        0 0 0 11px #1e1e22,
        0 0 0 13px #3a3a40,
        0 60px 120px rgba(0,0,0,.95),
        0 20px 40px rgba(0,0,0,.6);

    /* Espaço para dynamic island e home indicator */
    padding-top: 58px !important;
    padding-bottom: 30px !important;
    overflow: hidden !important;
    position: relative !important;
    min-height: 820px !important;
}

/* ── Botões laterais simulados ──────────────────── */
.block-container::before {  /* botões volume esquerda */
    content: '';
    position: absolute;
    left: -20px; top: 160px;
    width: 6px; height: 80px;
    background: #2a2a2e;
    border-radius: 3px 0 0 3px;
    box-shadow: 0 -50px 0 #2a2a2e, 0 -90px 0 #2a2a2e;
}
.block-container::after {   /* botão power direita */
    content: '';
    position: absolute;
    right: -20px; top: 200px;
    width: 6px; height: 90px;
    background: #2a2a2e;
    border-radius: 0 3px 3px 0;
}

/* ── Dynamic Island (notch) ─────────────────────── */
.dynamic-island {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 34px;
    background: #000;
    border-radius: 20px;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}
.di-camera { width:10px; height:10px; border-radius:50%; background:#1a1a1a;
    border:1px solid #333; }
.di-speaker { width:32px; height:5px; border-radius:3px; background:#111; }

/* ── Barra de status iOS ──────────────────────────── */
.status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 24px;
    height: 44px;
    margin-top: -10px;
    position: relative;
    z-index: 50;
}
.sb-time  { color: #fff; font-size: 15px; font-weight: 700; letter-spacing: -.3px; }
.sb-icons { display: flex; gap: 5px; align-items: center; }
.sb-signal { display: flex; gap: 2px; align-items: flex-end; }
.sb-signal span { background: #fff; border-radius: 1px; width: 4px; }
.sb-battery {
    width: 24px; height: 12px; border: 1.5px solid #fff; border-radius: 3px;
    position: relative;
    display: flex; align-items: center; padding: 1.5px;
}
.sb-battery::after {
    content:''; position:absolute; right:-4px; top:50%; transform:translateY(-50%);
    width:3px; height:5px; background:#fff; border-radius:0 1px 1px 0;
}
.sb-battery-fill { background:#fff; border-radius:1px; height:100%; width:75%; }

/* ── Home indicator ───────────────────────────────── */
.home-indicator {
    width: 130px; height: 5px;
    background: rgba(255,255,255,.3);
    border-radius: 3px;
    margin: 16px auto 0;
}

/* ── TELA IDLE ─────────────────────────────────────── */
.idle-screen {
    padding: 16px 24px 24px;
    text-align: center;
    color: #fff;
    min-height: 720px;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.phone-dialer-header {
    font-size: .78rem;
    color: rgba(255,255,255,.45);
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.phone-number-display {
    font-size: 2.2rem;
    font-weight: 300;
    letter-spacing: .08em;
    color: #fff;
    margin: 4px 0 2px;
}
.phone-contact-name {
    font-size: 1.3rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 4px;
}
.phone-contact-sub {
    font-size: .82rem;
    color: rgba(255,255,255,.5);
    margin-bottom: 40px;
}
.phone-contact-avatar {
    width: 100px; height: 100px; border-radius: 50%;
    background: linear-gradient(135deg, #ee1d23 0%, #c01018 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 2.6rem;
    margin: 0 auto 24px;
    box-shadow: 0 8px 32px rgba(238,29,35,.4);
}
.phone-contact-avatar img {
    width: 100%; height: 100%; border-radius: 50%; object-fit: cover;
}
.dialer-actions {
    display: flex;
    justify-content: center;
    gap: 32px;
    margin: 20px 0;
}
.dialer-action-btn {
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    background: rgba(255,255,255,.1);
    border: none; border-radius: 50%;
    width: 64px; height: 64px;
    font-size: 1.4rem; cursor: pointer; color: #fff;
}
.dialer-action-label { font-size: .65rem; color: rgba(255,255,255,.6); margin-top: -24px; }
.call-btn-green {
    width: 72px; height: 72px; border-radius: 50%;
    background: #22c55e;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.8rem; cursor: pointer; border: none;
    box-shadow: 0 0 0 0 rgba(34,197,94,.5);
    animation: call-btn-pulse 2s ease-in-out infinite;
    margin: 0 auto;
}
@keyframes call-btn-pulse {
    0%,100%{ box-shadow: 0 0 0 0 rgba(34,197,94,.5); }
    50%    { box-shadow: 0 0 0 14px rgba(34,197,94,.0); }
}

/* ── TELA RINGING ──────────────────────────────────── */
.ringing-screen {
    padding: 16px 24px;
    text-align: center;
    color: #fff;
    min-height: 720px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
}
.ringing-contact-name { font-size: 1.5rem; font-weight: 600; margin-bottom: 4px; }
.ringing-status {
    font-size: .9rem; color: rgba(255,255,255,.6); margin-bottom: 40px;
}
.ringing-avatar {
    width: 120px; height: 120px; border-radius: 50%;
    background: linear-gradient(135deg, #ee1d23 0%, #c01018 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem;
    margin: 0 auto 32px;
    animation: ring-pulse 1.6s ease-out infinite;
    overflow: hidden;
}
.ringing-avatar img { width:100%; height:100%; border-radius:50%; object-fit:cover; }
@keyframes ring-pulse {
    0%   { box-shadow: 0 0 0 0px rgba(238,29,35,.6); }
    40%  { box-shadow: 0 0 0 24px rgba(238,29,35,.15); }
    100% { box-shadow: 0 0 0 48px rgba(238,29,35,.0); }
}
.ringing-actions {
    display: flex;
    justify-content: space-around;
    width: 100%;
    padding-bottom: 16px;
}
.btn-decline {
    width: 72px; height: 72px; border-radius: 50%;
    background: #ef4444; border: none; cursor: pointer;
    font-size: 1.8rem; color: #fff;
    box-shadow: 0 4px 16px rgba(239,68,68,.4);
}
.btn-accept {
    width: 72px; height: 72px; border-radius: 50%;
    background: #22c55e; border: none; cursor: pointer;
    font-size: 1.8rem; color: #fff;
    box-shadow: 0 4px 16px rgba(34,197,94,.4);
}

/* ── TELA CONNECTED ─────────────────────────────────── */
.call-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 24px 12px;
    border-bottom: 1px solid rgba(255,255,255,.06);
}
.call-status {
    display: flex; align-items: center; gap: 6px;
}
.call-dot { width:8px; height:8px; border-radius:50%; background:#22c55e;
    animation: dot-blink 2s ease-in-out infinite; }
@keyframes dot-blink { 0%,100%{opacity:1;} 50%{opacity:.3;} }
.call-label { color: #22c55e; font-size: .82rem; font-weight: 600; }
.call-timer { color: rgba(255,255,255,.5); font-size: .82rem; font-variant-numeric: tabular-nums; }

.agent-section {
    display: flex; flex-direction: column; align-items: center;
    padding: 20px 0 12px;
}
.agent-avatar-wrap {
    position: relative;
    width: 120px; height: 120px;
}
.agent-avatar-wrap.speaking::before {
    content:''; position:absolute; inset:-10px; border-radius:50%;
    border: 2px solid rgba(238,29,35,.7);
    animation: speak-wave 1s ease-out infinite;
}
.agent-avatar-wrap.speaking::after {
    content:''; position:absolute; inset:-22px; border-radius:50%;
    border: 2px solid rgba(238,29,35,.35);
    animation: speak-wave 1s .25s ease-out infinite;
}
@keyframes speak-wave {
    0%  { transform:scale(.85); opacity:.9; }
    100%{ transform:scale(1.15); opacity:0; }
}
.agent-photo {
    width:120px; height:120px; border-radius:50%; object-fit:cover;
    border: 2.5px solid rgba(238,29,35,.6);
    box-shadow: 0 0 20px rgba(238,29,35,.3);
    display: block;
}
.agent-placeholder {
    width:120px; height:120px; border-radius:50%;
    background: linear-gradient(135deg,#ee1d23,#c01018);
    display:flex; align-items:center; justify-content:center;
    font-size:3rem;
    border: 2.5px solid rgba(238,29,35,.6);
    box-shadow: 0 0 20px rgba(238,29,35,.3);
    overflow: hidden;
}
.headset-pill {
    position:absolute; bottom:4px; right:4px;
    background:#ee1d23; border-radius:12px;
    padding:3px 7px; font-size:.65rem; color:#fff; font-weight:700;
    border:2px solid #0d0d0f;
}
.agent-name  { color:#fff; font-size:1.1rem; font-weight:700; margin-top:12px; }
.agent-role  { color:rgba(255,255,255,.45); font-size:.75rem; margin-top:2px; }

/* Equalizer boca */
.eq { display:flex; gap:3px; align-items:center; height:20px; margin-top:8px; }
.eq span { display:block; width:4px; height:3px; background:#ee1d23; border-radius:2px; }
.eq.on span { animation: eq-anim .5s ease-in-out infinite alternate; }
.eq span:nth-child(1){ animation-delay:.00s; }
.eq span:nth-child(2){ animation-delay:.08s; }
.eq span:nth-child(3){ animation-delay:.04s; }
.eq span:nth-child(4){ animation-delay:.12s; }
.eq span:nth-child(5){ animation-delay:.06s; }
.eq span:nth-child(6){ animation-delay:.10s; }
.eq span:nth-child(7){ animation-delay:.02s; }
@keyframes eq-anim {
    0%  { height:2px;  }
    30% { height:12px; }
    60% { height:20px; }
    100%{ height:8px;  }
}

/* Chat */
.chat-area {
    margin: 4px 16px;
    max-height: 240px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-bottom: 4px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,.1) transparent;
}
.msg-you {
    align-self: flex-end;
    background: #ee1d23;
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 8px 14px;
    font-size: .85rem;
    max-width: 85%;
}
.msg-ai {
    align-self: flex-start;
    background: rgba(255,255,255,.1);
    color: #fff;
    border-radius: 18px 18px 18px 4px;
    padding: 8px 14px;
    font-size: .85rem;
    max-width: 85%;
}
.msg-transfer {
    align-self: center;
    background: rgba(255,215,0,.15);
    border: 1px solid rgba(255,215,0,.4);
    color: #ffd700;
    border-radius: 12px;
    padding: 5px 14px;
    font-size: .75rem;
    font-weight: 600;
}

/* Input area */
.input-row {
    padding: 10px 16px 4px;
    border-top: 1px solid rgba(255,255,255,.07);
}
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,.08) !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    border-radius: 22px !important;
    color: #fff !important;
    font-size: .9rem !important;
    padding: 8px 16px !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,.3) !important;
}
div[data-testid="stTextInput"] label { display: none !important; }

/* End call button */
.end-row {
    display: flex;
    justify-content: center;
    padding: 12px 0 4px;
}
.btn-end-call {
    width: 64px; height: 64px; border-radius: 50%;
    background: #ef4444; border: none; cursor: pointer;
    font-size: 1.5rem; color: #fff;
    box-shadow: 0 4px 20px rgba(239,68,68,.45);
    transition: transform .15s;
}
.btn-end-call:hover { transform: scale(1.08); }

/* Spinner */
.stSpinner > div { color: rgba(255,255,255,.5) !important; }

/* Streamlit default button overrides */
div[data-testid="stButton"] button {
    border-radius: 22px !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# JAVASCRIPT — Ring tone (Web Audio) + Interrupção
# ─────────────────────────────────────────────────────
st.markdown("""
<script>
// ── Ring tone ─────────────────────────────────────────
window._clarinha_ring = function(onDone) {
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function playRing(startAt) {
            [440, 480].forEach(function(freq) {
                var osc  = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0, startAt);
                gain.gain.linearRampToValueAtTime(0.25, startAt + 0.08);
                gain.gain.setValueAtTime(0.25, startAt + 0.85);
                gain.gain.linearRampToValueAtTime(0, startAt + 1.0);
                osc.start(startAt);
                osc.stop(startAt + 1.1);
            });
        }
        playRing(ctx.currentTime + 0.1);
        playRing(ctx.currentTime + 2.3);
        setTimeout(function() {
            try { ctx.close(); } catch(e) {}
            if (onDone) onDone();
        }, 5000);
    } catch(e) {
        if (onDone) setTimeout(onDone, 5000);
    }
};

// ── Ambient (pink noise) ─────────────────────────────
window._ambientStarted = false;
window._clarinha_ambient = function() {
    if (window._ambientStarted) return;
    window._ambientStarted = true;
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var g = ctx.createGain(); g.gain.value = 0.03; g.connect(ctx.destination);
        var buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
        var d = buf.getChannelData(0);
        var b=[0,0,0,0,0,0,0];
        for(var i=0;i<d.length;i++){
            var w=Math.random()*2-1;
            b[0]=.99886*b[0]+w*.0555179; b[1]=.99332*b[1]+w*.0750759;
            b[2]=.96900*b[2]+w*.1538520; b[3]=.86650*b[3]+w*.3104856;
            b[4]=.55000*b[4]+w*.5329522; b[5]=-.7616*b[5]-w*.0168980;
            d[i]=(b[0]+b[1]+b[2]+b[3]+b[4]+b[5]+b[6]+w*.5362)/7; b[6]=w*.115926;
        }
        var src=ctx.createBufferSource(); src.buffer=buf; src.loop=true;
        src.connect(g); src.start();
    } catch(e) {}
};

// ── TTS controls ────────────────────────────────────
window._ttsAudio = null;
window._ttsSpeaking = false;
window._clarinha_stop_tts = function() {
    if (window._ttsAudio) {
        try { window._ttsAudio.pause(); window._ttsAudio.currentTime=0; } catch(e){}
        window._ttsAudio = null;
    }
    window._ttsSpeaking = false;
    document.querySelectorAll('.agent-avatar-wrap').forEach(function(e){ e.classList.remove('speaking'); });
    document.querySelectorAll('.eq').forEach(function(e){ e.classList.remove('on'); });
};

// Para TTS quando microfone é ativado
var _origGUM = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
navigator.mediaDevices.getUserMedia = async function(c){
    if(c && c.audio) window._clarinha_stop_tts();
    return _origGUM(c);
};
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# INICIALIZAÇÃO DE APIS
# ─────────────────────────────────────────────────────
try:
    client_eleven = ElevenLabs(api_key=st.secrets["ELEVEN_API_KEY"])
    aws_auth = {
        "aws_access_key_id":     st.secrets["AWS_ACCESS_KEY"],
        "aws_secret_access_key": st.secrets["AWS_SECRET_KEY"],
        "region_name":           "us-east-1",
    }
    bedrock           = boto3.client("bedrock-runtime", **aws_auth)
    s3_client         = boto3.client("s3",          **aws_auth)
    transcribe_client = boto3.client("transcribe",  **aws_auth)
except Exception as e:
    st.error(f"Erro nos Secrets: {e}")
    st.stop()

# ─────────────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────────────
_defaults = {
    "call_state":      "idle",      # idle | ringing | connected
    "call_start":      0.0,
    "historico":       [],          # [{"u": str, "a": str}]  — "u" nunca vazio
    "saudacao_feita":  False,
    "perfil_cliente":  "prospect",
    "last_mic_key":    None,        # evita reprocessar mesmo áudio
    "ring_count":      0,           # ID único por chamada — garante ring fresco
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

def _avatar_inner(size_px: int = 120) -> str:
    s = size_px
    if HAS_PHOTO and _PHOTO_URI:
        return f'<img src="{_PHOTO_URI}" class="agent-photo" style="width:{s}px;height:{s}px;" alt="Clarinha"/>'
    # CSS avatar fallback quando não há foto
    return (
        f'<div class="agent-placeholder" style="width:{s}px;height:{s}px;">'
        f'<img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMjAgMTIwIj48Y2lyY2xlIGN4PSI2MCIgY3k9IjQ1IiByPSIyNCIgZmlsbD0iI2ZmZiIgb3BhY2l0eT0iLjkiLz48ZWxsaXBzZSBjeD0iNjAiIGN5PSI5NSIgcng9IjM2IiByeT0iMjgiIGZpbGw9IiNmZmYiIG9wYWNpdHk9Ii45Ii8+PC9zdmc+" '
        f'style="width:{s}px;height:{s}px;border-radius:50%;object-fit:cover;" alt="Clarinha"/>'
        f'</div>'
    )


def _ios_statusbar() -> str:
    now = time.strftime("%H:%M")
    return f"""
    <div class="dynamic-island">
      <div class="di-speaker"></div>
      <div class="di-camera"></div>
    </div>
    <div class="status-bar">
      <span class="sb-time">{now}</span>
      <div class="sb-icons">
        <div class="sb-signal">
          <span style="height:5px"></span>
          <span style="height:8px"></span>
          <span style="height:11px"></span>
          <span style="height:14px"></span>
        </div>
        <span style="color:#fff;font-size:11px;">WiFi</span>
        <div class="sb-battery">
          <div class="sb-battery-fill"></div>
        </div>
      </div>
    </div>
    """


def transcrever_audio(audio_bytes: bytes) -> str | None:
    """
    Transcrição em 2 tentativas:
      1. ElevenLabs Scribe STT  → rápido (~2-3s), suporta webm nativamente
      2. Amazon Transcribe       → fallback (~20-30s) se Scribe falhar
    """
    import io

    # ── 1. ElevenLabs Scribe (rápido) ─────────────────────────────────────
    try:
        buf = io.BytesIO(audio_bytes)
        buf.name = "audio.webm"          # hint de formato para a API
        result = client_eleven.speech_to_text.convert(
            audio=buf,
            model_id="scribe_v1",
            language_code="pt",          # força português
        )
        texto = (result.text or "").strip()
        if texto:
            return texto
    except Exception:
        pass  # cai no fallback silenciosamente

    # ── 2. Amazon Transcribe (fallback) ────────────────────────────────────
    job = f"clarinha_{int(time.time())}"
    bkt = "audio-claro-poc-andy"
    key = f"{job}.webm"
    try:
        s3_client.put_object(Bucket=bkt, Key=key, Body=audio_bytes)
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job,
            Media={"MediaFileUri": f"s3://{bkt}/{key}"},
            MediaFormat="webm",
            LanguageCode="pt-BR",
        )
        for _ in range(60):          # máx 60s (era 120s)
            st_ = transcribe_client.get_transcription_job(
                TranscriptionJobName=job
            )["TranscriptionJob"]["TranscriptionJobStatus"]
            if st_ == "COMPLETED":
                break
            if st_ == "FAILED":
                return None
            time.sleep(1)
        url = transcribe_client.get_transcription_job(
            TranscriptionJobName=job
        )["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        return requests.get(url).json()["results"]["transcripts"][0]["transcript"]
    except Exception as e:
        st.error(f"Transcrição falhou: {e}")
        return None


def tocar_audio(texto: str):
    try:
        chunks = client_eleven.text_to_speech.convert(
            text=texto,
            voice_id="RGymW84CSmfVugnA5tvA",
            model_id="eleven_turbo_v2_5",
            voice_settings={
                "stability": 0.50, "similarity_boost": 0.85,
                "style": 0.30, "use_speaker_boost": True,
            },
        )
        b64 = base64.b64encode(b"".join(chunks)).decode()
        st.markdown(f"""
        <audio id="tts-{int(time.time()*1000)}" autoplay
          onplay="
            window._ttsAudio=this; window._ttsSpeaking=true;
            document.querySelectorAll('.agent-avatar-wrap').forEach(e=>e.classList.add('speaking'));
            document.querySelectorAll('.eq').forEach(e=>e.classList.add('on'));
            window._clarinha_ambient && window._clarinha_ambient();
          "
          onended="window._clarinha_stop_tts();">
          <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"ElevenLabs: {e}")


def _chamar_bedrock(msgs: list, ctx_extra: str = "") -> str:
    """Tenta modelos em ordem de preferência."""
    body_data = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 180,   # voz precisa de respostas curtas e rápidas
        "system": SYSTEM_PROMPT + ctx_extra,
        "messages": msgs,
    }
    for model_id in BEDROCK_MODELS:
        try:
            r = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(body_data),
            )
            return json.loads(r["body"].read())["content"][0]["text"]
        except Exception:
            continue
    raise RuntimeError("Nenhum modelo Bedrock disponível")


def obter_resposta(pergunta: str) -> tuple[str, bool]:
    # Guardrail de entrada
    av = classificar_input(pergunta)
    if av["resposta_guardrail"]:
        return av["resposta_guardrail"], False

    # Contexto extra para perguntas residenciais
    ctx_extra = ""
    if any(p in pergunta.lower() for p in ["internet","fibra","tv","residencial","gpon","mega"]):
        ctx_extra = "\n\n" + resumo_para_contexto(st.session_state.perfil_cliente)

    # Monta histórico — NUNCA inclui turnos com "u" vazio
    msgs = []
    for t in st.session_state.historico:
        if t["u"]:  # pula a saudação inicial (u vazio)
            msgs.append({"role": "user",      "content": t["u"]})
            msgs.append({"role": "assistant",  "content": t["a"]})
    msgs.append({"role": "user", "content": pergunta})

    try:
        resp = _chamar_bedrock(msgs, ctx_extra)
    except Exception:
        # Fallback humanizado quando Bedrock indisponível
        p = pergunta.lower()
        if "endereç" in p:
            resp = "Entendo! Por segurança, não é possível alterar o endereço após o pedido ser gerado. Posso orientar sobre o cancelamento e novo pedido, tudo bem?"
        elif "instalação" in p or "técnico" in p:
            resp = "Você pode consultar ou reagendar sua visita técnica pelo app Minha Claro Residencial, em Minhas Visitas. Posso ajudar com mais alguma coisa?"
        elif "chip" in p or "esim" in p or "e-sim" in p:
            resp = "A ativação do chip ou eSIM leva até 48 horas após o recebimento. A portabilidade ocorre logo depois. Precisa de mais informações?"
        elif "fatura" in p or "boleto" in p or "cobrança" in p:
            resp = "Você pode consultar sua fatura pelo app Minha Claro ou pelo site claro.com.br. Posso te conectar com nosso time financeiro se precisar."
        elif "cancelar" in p or "cancelamento" in p:
            resp = "Entendo. Para cancelamentos, preciso te conectar com um especialista que poderá avaliar as melhores opções para você."
        else:
            resp = "Claro! Estou aqui para te ajudar. Pode me contar mais detalhes sobre sua dúvida para eu te auxiliar melhor?"

    resp = sanitizar_resposta(resp)
    return resp, deve_transferir_humano(resp)


# ─────────────────────────────────────────────────────
# ══════════════ TELA: IDLE ═══════════════════════════
# ─────────────────────────────────────────────────────
if st.session_state.call_state == "idle":

    st.markdown(_ios_statusbar(), unsafe_allow_html=True)

    avatar_idle = ""
    if HAS_PHOTO and _PHOTO_URI:
        avatar_idle = f'<img src="{_PHOTO_URI}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" alt="Clarinha"/>'
    else:
        avatar_idle = "👩‍💼"

    st.markdown(f"""
    <div class="idle-screen">
      <div style="text-align:center; padding-top: 20px;">
        <div class="phone-contact-avatar">{avatar_idle}</div>
        <div class="phone-contact-name">{NOME_ASSISTENTE}</div>
        <div style="color:rgba(255,255,255,.5);font-size:.85rem;margin-top:4px;">Claro Pós-Venda</div>
        <div class="phone-number-display" style="margin-top:16px;">{NUMERO_CLARO}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Botão Ligar — centralizado, estilo iOS call button
    st.markdown("""
    <style>
    /* Centraliza e estiliza o botão Ligar em qualquer largura */
    div[data-testid="stButton"] {
        display: flex !important;
        justify-content: center !important;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        width: 180px !important;
        border-radius: 40px !important;
        background: #22c55e !important;
        border-color: #22c55e !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        padding: 14px 0 !important;
        letter-spacing: .03em !important;
        box-shadow: 0 4px 24px rgba(34,197,94,.45) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    if st.button("📞  Ligar", key="btn_ligar", type="primary"):
        st.session_state.call_state = "ringing"
        st.session_state.ring_count += 1   # chave única → ring sempre toca
        st.rerun()

    st.markdown('<div class="home-indicator"></div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.selectbox("Perfil", ["prospect", "base"], key="perfil_cliente")


# ─────────────────────────────────────────────────────
# ══════════════ TELA: RINGING ════════════════════════
# ─────────────────────────────────────────────────────
elif st.session_state.call_state == "ringing":

    st.markdown(_ios_statusbar(), unsafe_allow_html=True)

    avatar_ring = (
        f'<img src="{_PHOTO_URI}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" alt="Clarinha"/>'
        if (HAS_PHOTO and _PHOTO_URI) else "👩‍💼"
    )

    _rc = st.session_state.ring_count   # chave única por chamada

    st.markdown(f"""
    <div class="ringing-screen">
      <div>
        <div style="color:rgba(255,255,255,.55);font-size:.82rem;margin-bottom:6px;">Claro Pós-Venda</div>
        <div class="ringing-contact-name">{NOME_ASSISTENTE}</div>
        <div class="ringing-status" id="ring-status-text">Chamando...</div>
        <div class="ringing-avatar">{avatar_ring}</div>
        <div style="color:rgba(255,255,255,.45);font-size:.85rem;">{NUMERO_CLARO}</div>
      </div>
    </div>

    <script>
    (function() {{
        // Chave única por chamada — garante que o ring toca sempre que usuário apertar Ligar
        var ringKey = 'ring_{_rc}';
        if (sessionStorage.getItem(ringKey)) return;
        sessionStorage.setItem(ringKey, '1');

        // Ring tone auto-contido (não depende de função global)
        function playRing(onDone) {{
            try {{
                var ctx = new (window.AudioContext || window.webkitAudioContext)();
                function tone(startAt) {{
                    [440, 480].forEach(function(freq) {{
                        var osc  = ctx.createOscillator();
                        var gain = ctx.createGain();
                        osc.connect(gain); gain.connect(ctx.destination);
                        osc.type = 'sine'; osc.frequency.value = freq;
                        gain.gain.setValueAtTime(0, startAt);
                        gain.gain.linearRampToValueAtTime(0.28, startAt + 0.08);
                        gain.gain.setValueAtTime(0.28, startAt + 0.85);
                        gain.gain.linearRampToValueAtTime(0, startAt + 1.0);
                        osc.start(startAt); osc.stop(startAt + 1.1);
                    }});
                }}
                tone(ctx.currentTime + 0.1);
                tone(ctx.currentTime + 2.3);
                setTimeout(function() {{
                    try {{ ctx.close(); }} catch(e) {{}}
                    if (onDone) onDone();
                }}, 5000);
            }} catch(e) {{
                if (onDone) setTimeout(onDone, 5000);
            }}
        }}

        playRing(function() {{
            // Após os 2 toques: auto-clica "Atender"
            var tries = 0;
            function clickAtender() {{
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].textContent.includes('Atender')) {{
                        btns[i].click(); return;
                    }}
                }}
                if (++tries < 30) setTimeout(clickAtender, 200);
            }}
            clickAtender();
        }});
    }})();
    </script>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("📵 Recusar", key="btn_recusar", use_container_width=True):
            st.session_state.call_state = "idle"
            st.rerun()
    with col3:
        if st.button("📞 Atender", key="btn_atender", use_container_width=True, type="primary"):
            st.session_state.call_state     = "connected"
            st.session_state.call_start     = time.time()
            st.session_state.saudacao_feita = False
            st.rerun()

    st.markdown('<div class="home-indicator"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ══════════════ TELA: CONNECTED ══════════════════════
# ─────────────────────────────────────────────────────
elif st.session_state.call_state == "connected":

    elapsed_call = time.time() - st.session_state.call_start

    st.markdown(_ios_statusbar(), unsafe_allow_html=True)

    # ── Header da chamada ──────────────────────────────
    st.markdown(f"""
    <div class="call-header">
      <div class="call-status">
        <span class="call-dot"></span>
        <span class="call-label">Em chamada</span>
      </div>
      <span class="call-timer" id="call-timer">{int(elapsed_call//60):02d}:{int(elapsed_call%60):02d}</span>
    </div>
    <script>
    (function(){{
        // Timer
        var s = Date.now() - {int(elapsed_call*1000)};
        function tick(){{
            var t = Math.floor((Date.now()-s)/1000);
            var el = document.getElementById('call-timer');
            if(el) el.textContent = String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0');
            setTimeout(tick, 500);
        }}
        tick();

        // Som ambiente call center — inicia ao entrar na chamada (não só no TTS)
        if (!window._ambientStarted) {{
            window._ambientStarted = true;
            try {{
                var actx = new (window.AudioContext || window.webkitAudioContext)();
                var gn = actx.createGain(); gn.gain.value = 0.025; gn.connect(actx.destination);
                var buf = actx.createBuffer(1, actx.sampleRate * 2, actx.sampleRate);
                var d = buf.getChannelData(0);
                var b=[0,0,0,0,0,0,0];
                for(var i=0;i<d.length;i++){{
                    var w=Math.random()*2-1;
                    b[0]=.99886*b[0]+w*.0555179; b[1]=.99332*b[1]+w*.0750759;
                    b[2]=.96900*b[2]+w*.1538520; b[3]=.86650*b[3]+w*.3104856;
                    b[4]=.55000*b[4]+w*.5329522; b[5]=-.7616*b[5]-w*.0168980;
                    d[i]=(b[0]+b[1]+b[2]+b[3]+b[4]+b[5]+b[6]+w*.5362)/7; b[6]=w*.115926;
                }}
                var src=actx.createBufferSource(); src.buffer=buf; src.loop=true;
                src.connect(gn); src.start();
            }} catch(e) {{}}
        }}
    }})();
    </script>
    """, unsafe_allow_html=True)

    # ── Avatar da Clarinha ─────────────────────────────
    eq_bars = "".join(f'<span style="height:{h}px"></span>' for h in [4,10,18,22,16,12,6])
    st.markdown(f"""
    <div class="agent-section">
      <div class="agent-avatar-wrap" id="avatar-wrap">
        {_avatar_inner(120)}
        <div class="headset-pill">🎧 ao vivo</div>
      </div>
      <div class="agent-name">{NOME_ASSISTENTE}</div>
      <div class="agent-role">Assistente Virtual · Claro Pós-Venda</div>
      <div class="eq" id="eq-bar">{eq_bars}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Saudação inicial ───────────────────────────────
    if not st.session_state.saudacao_feita:
        # NÃO adiciona ao histórico com "u" vazio — guarda separado
        st.session_state.saudacao_feita = True
        tocar_audio(SAUDACAO_INICIAL)
        st.session_state.historico.append({"u": "", "a": SAUDACAO_INICIAL})

    # ── Chat ───────────────────────────────────────────
    msgs_html = ""
    for t in st.session_state.historico:
        if t["a"] and not t["u"]:  # saudação inicial
            msgs_html += f'<div class="msg-ai">{t["a"]}</div>'
        else:
            if t["u"]:
                msgs_html += f'<div class="msg-you">{t["u"]}</div>'
            if t["a"]:
                msgs_html += f'<div class="msg-ai">{t["a"]}</div>'

    if msgs_html:
        st.markdown(f"""
        <div class="chat-area" id="chat">{msgs_html}</div>
        <script>
        (function(){{ var c=document.getElementById('chat'); if(c) c.scrollTop=c.scrollHeight; }})();
        </script>
        """, unsafe_allow_html=True)

    # ── Input ──────────────────────────────────────────
    st.markdown('<div class="input-row">', unsafe_allow_html=True)

    audio = mic_recorder(
        start_prompt="🔴 Gravar",
        stop_prompt="🟢 Enviar",
        key="mic_rec",
    )

    c1, c2 = st.columns([5, 1])
    with c1:
        texto = st.text_input("Mensagem", placeholder="Digite sua mensagem...",
                              label_visibility="collapsed")
    with c2:
        enviar = st.button("↩", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Processamento (sem reprocessar o mesmo áudio) ──
    pergunta = None

    if audio:
        audio_id = id(audio["bytes"])
        if audio_id != st.session_state.last_mic_key:
            st.session_state.last_mic_key = audio_id
            with st.spinner("Transcrevendo..."):
                pergunta = transcrever_audio(audio["bytes"])
                if not pergunta:
                    st.warning("Não entendi o áudio. Tente novamente.")

    elif enviar and texto.strip():
        pergunta = texto.strip()

    if pergunta:
        with st.spinner(f"{NOME_ASSISTENTE} está pensando..."):
            resposta, transferir = obter_resposta(pergunta)

        st.session_state.historico.append({"u": pergunta, "a": resposta})

        if transferir:
            st.markdown('<div class="msg-transfer">⚡ Transferindo para especialista...</div>',
                        unsafe_allow_html=True)
            tocar_audio(RESPOSTA_TRANSFERENCIA)
        else:
            tocar_audio(resposta)

        st.rerun()

    # ── Encerrar chamada ───────────────────────────────
    st.markdown('<div class="end-row">', unsafe_allow_html=True)
    if st.button("📵", key="btn_end", help="Encerrar chamada"):
        st.session_state.call_state    = "idle"
        st.session_state.historico     = []
        st.session_state.saudacao_feita = False
        st.session_state.last_mic_key  = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="home-indicator"></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.selectbox("Perfil do cliente", ["prospect", "base"], key="perfil_cliente")
        st.caption("prospect = novo | base = já cliente")
