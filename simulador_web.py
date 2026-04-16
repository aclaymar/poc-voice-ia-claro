import streamlit as st
import boto3
import json
from elevenlabs.client import ElevenLabs
import base64
import time
import requests
from streamlit_mic_recorder import mic_recorder
from contexto import SYSTEM_PROMPT, SAUDACAO_INICIAL, RESPOSTA_TRANSFERENCIA, NOME_ASSISTENTE
from guardrails import classificar_input, deve_transferir_humano, sanitizar_resposta
from portfolio import resumo_para_contexto
import os

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{NOME_ASSISTENTE} · Claro Pós-Venda",
    page_icon="📞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

NUMERO_CLARO = "0800 738 0001"
CLARINHA_PHOTO = "img/clarinha.png"  # coloque aqui a foto da Clarinha
HAS_PHOTO = os.path.exists(CLARINHA_PHOTO)

# ─────────────────────────────────────────────────────
# CSS GLOBAL — tema escuro estilo apresentação
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
/* Reset Streamlit */
.stApp { background: linear-gradient(135deg,#080c1f 0%,#0f1535 55%,#0a1028 100%) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 480px; margin: 0 auto; }

/* ── TELA IDLE ───────────────────────────── */
.idle-screen {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    min-height:100vh; padding:32px 24px; text-align:center;
}
.brand-badge {
    display:inline-flex; align-items:center; gap:8px;
    background:rgba(238,29,35,0.18); border:1px solid rgba(238,29,35,0.45);
    border-radius:24px; padding:6px 18px; margin-bottom:28px;
    color:#ff6b6b; font-size:.82rem; font-weight:600; letter-spacing:.04em;
}
.voiceia-title {
    font-size:3.2rem; font-weight:900; color:#fff;
    letter-spacing:-.02em; line-height:1;
}
.voiceia-title span { color:#ee1d23; }
.idle-subtitle {
    color:rgba(255,255,255,.55); font-size:.95rem; margin:10px 0 36px;
}
.number-display {
    background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12);
    border-radius:16px; padding:20px 32px; margin-bottom:32px;
}
.number-label { color:rgba(255,255,255,.45); font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; }
.number-value { color:#fff; font-size:1.9rem; font-weight:700; letter-spacing:.04em; margin-top:4px; }
.number-sub   { color:rgba(255,255,255,.4); font-size:.78rem; margin-top:4px; }
.btn-call {
    display:inline-flex; align-items:center; gap:10px;
    background:linear-gradient(135deg,#22c55e,#16a34a);
    color:#fff; font-size:1.1rem; font-weight:700;
    border:none; border-radius:999px; padding:18px 48px;
    cursor:pointer; box-shadow:0 0 32px rgba(34,197,94,.45);
    transition:transform .15s, box-shadow .15s;
}
.btn-call:hover { transform:scale(1.05); box-shadow:0 0 48px rgba(34,197,94,.6); }
.stats-row {
    display:flex; gap:16px; margin-top:40px; width:100%;
}
.stat-card {
    flex:1; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08);
    border-radius:14px; padding:14px 8px; text-align:center;
}
.stat-value { color:#ee1d23; font-size:1.25rem; font-weight:800; }
.stat-label { color:rgba(255,255,255,.45); font-size:.7rem; margin-top:2px; }

/* ── TELA RINGING ────────────────────────── */
.ring-screen {
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    min-height:100vh; padding:32px 24px; text-align:center;
}
.claro-logo-ring { margin-bottom:12px; }
.ring-company { color:rgba(255,255,255,.6); font-size:.85rem; letter-spacing:.06em; text-transform:uppercase; }
.ring-number  { color:#fff; font-size:2.4rem; font-weight:800; letter-spacing:.06em; margin:6px 0; }
.ring-type    { color:rgba(255,255,255,.45); font-size:.85rem; margin-bottom:48px; }
.ring-avatar-wrap { position:relative; margin-bottom:40px; }
.ring-avatar {
    width:100px; height:100px; border-radius:50%;
    background:linear-gradient(135deg,#1e2a5e,#2d3a7a);
    border:3px solid rgba(255,255,255,.15);
    display:flex; align-items:center; justify-content:center;
    font-size:2.8rem;
    animation: ring-pulse 1.4s ease-in-out infinite;
}
@keyframes ring-pulse {
    0%,100%{ box-shadow:0 0 0 0 rgba(238,29,35,.5), 0 0 0 0 rgba(238,29,35,.25); }
    50%    { box-shadow:0 0 0 18px rgba(238,29,35,.0), 0 0 0 36px rgba(238,29,35,.0); }
    25%    { box-shadow:0 0 0 14px rgba(238,29,35,.25), 0 0 0 28px rgba(238,29,35,.1); }
}
.ring-status { color:rgba(255,255,255,.7); font-size:1rem; margin-bottom:8px; }
.ring-dots span {
    display:inline-block; width:6px; height:6px; border-radius:50%;
    background:#ee1d23; margin:0 3px;
    animation: dot-bounce .8s ease-in-out infinite;
}
.ring-dots span:nth-child(2) { animation-delay:.15s; }
.ring-dots span:nth-child(3) { animation-delay:.30s; }
@keyframes dot-bounce { 0%,100%{transform:translateY(0);opacity:.4;} 50%{transform:translateY(-5px);opacity:1;} }

/* ── TELA CONNECTED ──────────────────────── */
.call-header {
    display:flex; justify-content:space-between; align-items:center;
    padding:16px 20px; background:rgba(0,0,0,.3);
    border-bottom:1px solid rgba(255,255,255,.06);
}
.call-status-dot { width:8px; height:8px; border-radius:50%; background:#22c55e; display:inline-block;
    box-shadow:0 0 6px #22c55e; animation:status-blink 2s ease-in-out infinite; }
@keyframes status-blink { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.call-status-text { color:#22c55e; font-size:.82rem; font-weight:600; margin-left:7px; }
.call-timer { color:rgba(255,255,255,.6); font-size:.82rem; font-variant-numeric:tabular-nums; }

.avatar-section { display:flex; flex-direction:column; align-items:center; padding:28px 20px 16px; }
.avatar-ring-outer {
    position:relative; display:flex; align-items:center; justify-content:center;
    width:148px; height:148px;
}
.avatar-ring-outer.speaking::before {
    content:''; position:absolute; inset:-8px; border-radius:50%;
    border:2px solid rgba(238,29,35,.6);
    animation:speak-ring-1 1.0s ease-out infinite;
}
.avatar-ring-outer.speaking::after {
    content:''; position:absolute; inset:-18px; border-radius:50%;
    border:2px solid rgba(238,29,35,.3);
    animation:speak-ring-1 1.0s ease-out .25s infinite;
}
@keyframes speak-ring-1 {
    0%   { transform:scale(.88); opacity:.9; }
    100% { transform:scale(1.12); opacity:0; }
}
.avatar-img {
    width:132px; height:132px; border-radius:50%; object-fit:cover;
    border:3px solid rgba(238,29,35,.7);
    box-shadow:0 0 24px rgba(238,29,35,.35);
}
.avatar-placeholder {
    width:132px; height:132px; border-radius:50%;
    background:linear-gradient(135deg,#1a2260,#2c3a8a,#1a2260);
    border:3px solid rgba(238,29,35,.7);
    box-shadow:0 0 24px rgba(238,29,35,.35);
    display:flex; align-items:center; justify-content:center;
    font-size:3.5rem; position:relative; overflow:hidden;
}
.headset-badge {
    position:absolute; bottom:8px; right:8px;
    background:#ee1d23; border-radius:50%; width:32px; height:32px;
    display:flex; align-items:center; justify-content:center;
    font-size:1rem; border:2px solid #0f1535;
    box-shadow:0 2px 8px rgba(0,0,0,.5);
}
.agent-name { color:#fff; font-size:1.15rem; font-weight:700; margin-top:14px; }
.agent-role { color:rgba(255,255,255,.45); font-size:.8rem; margin-top:2px; }

/* Equalizer (boca mexendo) */
.equalizer { display:flex; gap:3px; align-items:center; height:24px; margin-top:10px; }
.equalizer.active span {
    animation:eq-bar .55s ease-in-out infinite alternate;
}
.equalizer span {
    display:block; width:4px; background:#ee1d23; border-radius:2px;
    height:4px; transition:height .1s;
}
.equalizer span:nth-child(1){ animation-delay:.00s; }
.equalizer span:nth-child(2){ animation-delay:.10s; }
.equalizer span:nth-child(3){ animation-delay:.05s; }
.equalizer span:nth-child(4){ animation-delay:.15s; }
.equalizer span:nth-child(5){ animation-delay:.08s; }
.equalizer span:nth-child(6){ animation-delay:.12s; }
.equalizer span:nth-child(7){ animation-delay:.03s; }
@keyframes eq-bar {
    0%  { height:3px;  }
    25% { height:14px; }
    50% { height:22px; }
    75% { height:10px; }
    100%{ height:18px; }
}

/* Chat */
.chat-box {
    margin:0 16px; max-height:260px; overflow-y:auto;
    display:flex; flex-direction:column; gap:10px;
    padding:0 4px 8px;
    scrollbar-width:thin; scrollbar-color:rgba(255,255,255,.15) transparent;
}
.msg-user {
    align-self:flex-end; background:rgba(238,29,35,.18);
    border:1px solid rgba(238,29,35,.3); border-radius:14px 14px 2px 14px;
    color:#fff; padding:9px 14px; font-size:.88rem; max-width:88%;
}
.msg-ai {
    align-self:flex-start; background:rgba(255,255,255,.07);
    border:1px solid rgba(255,255,255,.1); border-radius:14px 14px 14px 2px;
    color:#fff; padding:9px 14px; font-size:.88rem; max-width:88%;
}
.msg-label { font-size:.7rem; opacity:.5; margin-bottom:3px; }
.transfer-badge {
    align-self:center; background:rgba(255,215,0,.15); border:1px solid rgba(255,215,0,.4);
    color:#ffd700; border-radius:24px; padding:5px 14px; font-size:.78rem; font-weight:600;
}

/* Input area */
.input-area {
    position:sticky; bottom:0;
    background:rgba(8,12,31,.95); backdrop-filter:blur(12px);
    border-top:1px solid rgba(255,255,255,.07);
    padding:14px 16px 20px;
}
.end-call-wrap { display:flex; justify-content:center; padding:16px 0 24px; }
.btn-end {
    background:linear-gradient(135deg,#ef4444,#b91c1c);
    color:#fff; border:none; border-radius:50%; width:60px; height:60px;
    font-size:1.4rem; cursor:pointer;
    box-shadow:0 0 24px rgba(239,68,68,.5);
    transition:transform .15s;
}
.btn-end:hover{ transform:scale(1.08); }

/* Hide Streamlit extras */
.stSpinner > div { color:rgba(255,255,255,.6) !important; }
div[data-testid="stTextInput"] input {
    background:rgba(255,255,255,.07) !important;
    border:1px solid rgba(255,255,255,.15) !important;
    border-radius:10px !important; color:#fff !important;
}
div[data-testid="stTextInput"] input::placeholder { color:rgba(255,255,255,.3) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# JAVASCRIPT — Ring tone + Ambient + Interrupção
# ─────────────────────────────────────────────────────
st.markdown("""
<script>
// ── Ring Tone (Web Audio API) ─────────────────────────
window._clarinha_tocar_toque = function(cb) {
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function ring(t) {
            [440, 480].forEach(function(freq) {
                var osc  = ctx.createOscillator();
                var gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.frequency.value = freq; osc.type = 'sine';
                gain.gain.setValueAtTime(0, t);
                gain.gain.linearRampToValueAtTime(0.28, t + 0.08);
                gain.gain.setValueAtTime(0.28, t + 0.9);
                gain.gain.linearRampToValueAtTime(0, t + 1.1);
                osc.start(t); osc.stop(t + 1.2);
            });
        }
        ring(ctx.currentTime + 0.2);
        ring(ctx.currentTime + 2.2);
        setTimeout(function(){ ctx.close(); if(cb) cb(); }, 4800);
    } catch(e) { if(cb) setTimeout(cb, 4800); }
};

// ── Ambient call center (pink noise) ─────────────────
window._ambientRunning = false;
window._ambientCtx = null;
window._clarinha_iniciar_ambiente = function() {
    if (window._ambientRunning) return;
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        window._ambientCtx = ctx;
        var gain = ctx.createGain(); gain.gain.value = 0.035; gain.connect(ctx.destination);
        var buf  = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
        var d    = buf.getChannelData(0);
        var b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
        for(var i=0;i<d.length;i++){
            var w=Math.random()*2-1;
            b0=.99886*b0+w*.0555179; b1=.99332*b1+w*.0750759; b2=.96900*b2+w*.1538520;
            b3=.86650*b3+w*.3104856; b4=.55000*b4+w*.5329522; b5=-.7616*b5-w*.0168980;
            d[i]=(b0+b1+b2+b3+b4+b5+b6+w*.5362)/7; b6=w*.115926;
        }
        var src = ctx.createBufferSource(); src.buffer=buf; src.loop=true;
        src.connect(gain); src.start();
        window._ambientRunning = true;
    } catch(e) {}
};

// ── Controle do áudio TTS ─────────────────────────────
window._clarinaAudio = null;
window._clarinhaParlando = false;

window._clarinha_parar = function() {
    if (window._clarinaAudio) {
        window._clarinaAudio.pause();
        window._clarinaAudio.currentTime = 0;
        window._clarinaAudio = null;
    }
    window._clarinhaParlando = false;
    document.querySelectorAll('.avatar-ring-outer').forEach(function(el){
        el.classList.remove('speaking');
    });
    document.querySelectorAll('.equalizer').forEach(function(el){
        el.classList.remove('active');
    });
    var status = document.getElementById('speaking-status');
    if (status) status.style.display = 'none';
};

// Para o áudio quando o microfone é ativado
var _origGUM = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
navigator.mediaDevices.getUserMedia = async function(c) {
    if (c && c.audio) window._clarinha_parar();
    return _origGUM(c);
};
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# INICIALIZAÇÃO DE APIs
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
except Exception:
    st.error("Secrets não configurados. Verifique ELEVEN_API_KEY, AWS_ACCESS_KEY e AWS_SECRET_KEY.")
    st.stop()

# ─────────────────────────────────────────────────────
# ESTADO DA SESSÃO
# ─────────────────────────────────────────────────────
defaults = {
    "call_state":      "idle",    # idle | ringing | connected
    "ring_start":      0.0,
    "call_start":      0.0,
    "historico":       [],
    "saudacao_feita":  False,
    "perfil_cliente":  "prospect",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

def _avatar_html(speaking: bool = False) -> str:
    speak_cls = "speaking" if speaking else ""
    eq_cls    = "active"   if speaking else ""
    bars = "".join(f'<span style="height:{h}px"></span>' for h in [6,14,20,24,18,14,8])
    if HAS_PHOTO:
        inner = f'<img src="{CLARINHA_PHOTO}" class="avatar-img" alt="Clarinha"/>'
    else:
        inner = (
            '<div class="avatar-placeholder">'
            '<span style="font-size:3.5rem">👩‍💼</span>'
            '<div class="headset-badge">🎧</div>'
            '</div>'
        )
    status_style = "display:block" if speaking else "display:none"
    return f"""
    <div class="avatar-section">
      <div class="avatar-ring-outer {speak_cls}">
        {inner}
      </div>
      <div class="agent-name">{NOME_ASSISTENTE}</div>
      <div class="agent-role">Assistente Virtual · Claro Pós-Venda</div>
      <div class="equalizer {eq_cls}">{bars}</div>
      <div id="speaking-status" style="{status_style}; color:rgba(255,255,255,.4); font-size:.75rem; margin-top:6px;">
        falando...
      </div>
    </div>
    """


def _fmt_timer(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def transcrever_audio(audio_bytes: bytes) -> str | None:
    job  = f"clarinha_{int(time.time())}"
    bkt  = "audio-claro-poc-andy"
    key  = f"{job}.webm"
    try:
        s3_client.put_object(Bucket=bkt, Key=key, Body=audio_bytes)
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job,
            Media={"MediaFileUri": f"s3://{bkt}/{key}"},
            MediaFormat="webm",
            LanguageCode="pt-BR",
        )
        for _ in range(120):
            status = transcribe_client.get_transcription_job(
                TranscriptionJobName=job
            )["TranscriptionJob"]["TranscriptionJobStatus"]
            if status == "COMPLETED":
                break
            if status == "FAILED":
                return None
            time.sleep(1)
        url = transcribe_client.get_transcription_job(
            TranscriptionJobName=job
        )["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        return requests.get(url).json()["results"]["transcripts"][0]["transcript"]
    except Exception as e:
        st.error(f"Transcribe: {e}")
        return None


def tocar_audio(texto: str):
    try:
        chunks = client_eleven.text_to_speech.convert(
            text=texto,
            voice_id="RGymW84CSmfVugnA5tvA",
            model_id="eleven_turbo_v2_5",
            voice_settings={"stability": 0.50, "similarity_boost": 0.85,
                            "style": 0.30, "use_speaker_boost": True},
        )
        b64 = base64.b64encode(b"".join(chunks)).decode()
        st.markdown(f"""
        <audio id="tts-audio" autoplay
               onplay="
                   window._clarinaAudio=this; window._clarinhaParlando=true;
                   document.querySelectorAll('.avatar-ring-outer').forEach(e=>e.classList.add('speaking'));
                   document.querySelectorAll('.equalizer').forEach(e=>e.classList.add('active'));
                   var s=document.getElementById('speaking-status'); if(s) s.style.display='block';
                   window._clarinha_iniciar_ambiente && window._clarinha_iniciar_ambiente();
               "
               onended="window._clarinha_parar();">
          <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
          (function(){{
            var a=document.getElementById('tts-audio');
            window._clarinaAudio=a; window._clarinhaParlando=true;
          }})();
        </script>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"ElevenLabs: {e}")


def obter_resposta(pergunta: str) -> tuple[str, bool]:
    av = classificar_input(pergunta)
    if av["resposta_guardrail"]:
        return av["resposta_guardrail"], False

    ctx_extra = ""
    if any(p in pergunta.lower() for p in ["internet","fibra","tv","residencial","gpon","mega","instalação"]):
        ctx_extra = "\n\n" + resumo_para_contexto(st.session_state.perfil_cliente)

    msgs = []
    for t in st.session_state.historico:
        msgs.append({"role": "user",      "content": t["u"]})
        msgs.append({"role": "assistant", "content": t["a"]})
    msgs.append({"role": "user", "content": pergunta})

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "system": SYSTEM_PROMPT + ctx_extra,
            "messages": msgs,
        })
        r = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0", body=body
        )
        resp = json.loads(r["body"].read())["content"][0]["text"]
    except Exception:
        p = pergunta.lower()
        if "endereç" in p:
            resp = "Entendo! Por segurança, o endereço não pode ser alterado após o pedido. Posso te orientar a cancelar e refazer."
        elif "instalação" in p or "técnico" in p:
            resp = "Você pode reagendar sua visita pelo app Minha Claro Residencial, em Minhas Visitas. Posso ajudar com mais algo?"
        elif "chip" in p or "esim" in p:
            resp = "A ativação leva até 48 horas após o recebimento. A portabilidade ocorre logo depois da ativação."
        else:
            resp = "Estou aqui para ajudar! Pode me contar mais sobre sua dúvida?"

    resp = sanitizar_resposta(resp)
    return resp, deve_transferir_humano(resp)


# ─────────────────────────────────────────────────────
# ═══════════════ TELA: IDLE ══════════════════════════
# ─────────────────────────────────────────────────────
if st.session_state.call_state == "idle":
    st.markdown(f"""
    <div class="idle-screen">
      <div class="brand-badge">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="#ff6b6b">
          <circle cx="7" cy="7" r="7"/>
        </svg>
        VOICE IA · CLARO
      </div>
      <div class="voiceia-title">Voice<span>IA</span></div>
      <div class="idle-subtitle">A Revolução no Atendimento E-commerce da Claro</div>

      <div class="number-display">
        <div class="number-label">Central de Pós-Venda</div>
        <div class="number-value">{NUMERO_CLARO}</div>
        <div class="number-sub">E-commerce · Celular · Residencial · Acessórios</div>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">24/7</div>
          <div class="stat-label">Disponível</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">~5 min</div>
          <div class="stat-label">TMO Médio</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">100%</div>
          <div class="stat-label">Satisfação</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button("📞  Ligar para a Claro", use_container_width=True, type="primary"):
            st.session_state.call_state = "ringing"
            st.session_state.ring_start = time.time()
            st.rerun()


# ─────────────────────────────────────────────────────
# ═══════════════ TELA: RINGING ═══════════════════════
# ─────────────────────────────────────────────────────
elif st.session_state.call_state == "ringing":
    elapsed = time.time() - st.session_state.ring_start

    st.markdown(f"""
    <div class="ring-screen">
      <div class="ring-company">CLARO BRASIL</div>
      <div class="ring-number">{NUMERO_CLARO}</div>
      <div class="ring-type">Pós-Venda E-commerce</div>

      <div class="ring-avatar-wrap">
        <div class="ring-avatar">🎧</div>
      </div>

      <div class="ring-status">Chamando</div>
      <div class="ring-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Toca o toque na primeira vez (elapsed < 0.5s)
    if elapsed < 0.5:
        st.markdown("""
        <script>
        (function(){
            var tries = 0;
            function tryPlay() {
                if (typeof window._clarinha_tocar_toque === 'function') {
                    window._clarinha_tocar_toque();
                } else if (tries++ < 20) {
                    setTimeout(tryPlay, 200);
                }
            }
            tryPlay();
        })();
        </script>
        """, unsafe_allow_html=True)

    # Auto-conecta após ~5 segundos (2 toques)
    if elapsed >= 5.0:
        st.session_state.call_state = "connected"
        st.session_state.call_start = time.time()
        st.session_state.saudacao_feita = False
        st.rerun()
    else:
        time.sleep(0.4)
        st.rerun()


# ─────────────────────────────────────────────────────
# ═══════════════ TELA: CONNECTED ═════════════════════
# ─────────────────────────────────────────────────────
elif st.session_state.call_state == "connected":
    elapsed_call = time.time() - st.session_state.call_start

    # ── Header da chamada ──────────────────────────────
    st.markdown(f"""
    <div class="call-header">
      <div>
        <span class="call-status-dot"></span>
        <span class="call-status-text">Em chamada · {NUMERO_CLARO}</span>
      </div>
      <div class="call-timer" id="call-timer">{_fmt_timer(elapsed_call)}</div>
    </div>
    <script>
    (function(){{
        var start = Date.now() - {int(elapsed_call * 1000)};
        function tick() {{
            var s = Math.floor((Date.now()-start)/1000);
            var el = document.getElementById('call-timer');
            if(el) el.textContent = String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
            setTimeout(tick, 500);
        }}
        tick();
    }})();
    </script>
    """, unsafe_allow_html=True)

    # ── Avatar da Clarinha ─────────────────────────────
    st.markdown(_avatar_html(speaking=False), unsafe_allow_html=True)

    # ── Saudação inicial (uma vez) ─────────────────────
    if not st.session_state.saudacao_feita:
        st.session_state.historico.append({"u": "", "a": SAUDACAO_INICIAL})
        st.session_state.saudacao_feita = True
        tocar_audio(SAUDACAO_INICIAL)

    # ── Histórico de conversa ──────────────────────────
    chat_msgs = ""
    for turno in st.session_state.historico:
        if turno["u"]:
            chat_msgs += f'<div class="msg-user"><div class="msg-label">Você</div>{turno["u"]}</div>'
        if turno["a"]:
            chat_msgs += f'<div class="msg-ai"><div class="msg-label">{NOME_ASSISTENTE}</div>{turno["a"]}</div>'

    if chat_msgs:
        st.markdown(f'<div class="chat-box" id="chat-box">{chat_msgs}</div>', unsafe_allow_html=True)
        st.markdown("""
        <script>
        (function(){ var c=document.getElementById('chat-box'); if(c) c.scrollTop=c.scrollHeight; })();
        </script>""", unsafe_allow_html=True)

    # ── Área de input ──────────────────────────────────
    st.markdown('<div class="input-area">', unsafe_allow_html=True)

    st.markdown("**🎙️ Falar**")
    audio = mic_recorder(
        start_prompt="🔴 Iniciar",
        stop_prompt="🟢 Enviar",
        key="mic",
    )

    col1, col2 = st.columns([4, 1])
    with col1:
        texto = st.text_input("", placeholder="Digite sua dúvida...", label_visibility="collapsed")
    with col2:
        enviar = st.button("↩", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Processamento ──────────────────────────────────
    pergunta = None

    if audio:
        with st.spinner("Transcrevendo..."):
            pergunta = transcrever_audio(audio["bytes"])
            if pergunta:
                st.success(f"🗣 **{pergunta}**")
            else:
                st.warning("Áudio não entendido. Tente novamente.")

    elif enviar and texto.strip():
        pergunta = texto.strip()

    if pergunta:
        with st.spinner(f"{NOME_ASSISTENTE} está pensando..."):
            resposta, transferir = obter_resposta(pergunta)

        st.session_state.historico.append({"u": pergunta, "a": resposta})

        if transferir:
            st.markdown(
                '<div class="transfer-badge">⚡ Transferindo para especialista...</div>',
                unsafe_allow_html=True,
            )
            tocar_audio(RESPOSTA_TRANSFERENCIA)
        else:
            tocar_audio(resposta)

        st.rerun()

    # ── Botão encerrar chamada ─────────────────────────
    st.markdown('<div class="end-call-wrap">', unsafe_allow_html=True)
    if st.button("📵", key="btn_encerrar", help="Encerrar chamada"):
        st.session_state.call_state = "idle"
        st.session_state.historico  = []
        st.session_state.saudacao_feita = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar oculta com config
    with st.sidebar:
        st.markdown("### Configurações")
        st.session_state.perfil_cliente = st.selectbox(
            "Perfil do cliente", ["prospect", "base"]
        )
        st.caption("prospect = novo cliente | base = já é cliente Claro")
