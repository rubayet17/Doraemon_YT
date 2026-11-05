import base64
import hashlib
import io
import os

import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

from llm_engine import call_master_brain, transcribe_audio

# ------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------
st.set_page_config(page_title="Doraemon MAS Control Hub", page_icon="🤖", layout="wide")

# ------------------------------------------------------------------
# Custom CSS: Fixed Sidebar + Sticky Mission Header + Sticky Tab Menu
# ------------------------------------------------------------------
# Tweak these 2 values if needed:
#   --sticky-top : Streamlit's own top toolbar height (Share / star / menu)
#   --hdr-h      : height of the Core Mission Metric header
st.markdown("""
<style>
    :root {
        --sticky-top: 3.75rem;
        --hdr-h: 3.4rem;
    }

    /* Fixed Sidebar */
    [data-testid="stSidebar"] {
        position: fixed;
        top: 0;
        bottom: 0;
        left: 0;
        z-index: 100;
    }

    /* Sticky Mission Metric header (always visible while scrolling) */
    div[data-testid="stElementContainer"]:has(.mission-header),
    div.element-container:has(.mission-header) {
        position: sticky;
        top: var(--sticky-top);
        z-index: 99;
        background-color: #ffffff;
    }
    .mission-header {
        height: var(--hdr-h);
        display: flex;
        align-items: center;
        background-color: #ffffff;
        font-size: 1.15rem;
        font-weight: 700;
        line-height: 1.3;
        overflow: hidden;
        margin: 0;
        padding: 0;
    }

    /* Sticky Tab Menu - applies to ALL tabs, so any new tab you add
       later automatically stays fixed under the header */
    /* The tab bar sits inside a small wrapper, so we make the wrapper itself
       (a direct child of the tall tabs container) sticky. */
    [data-testid="stTabs"] [data-baseweb="tabs"] > div:has([data-baseweb="tab-list"]),
    [data-testid="stTabs"] [data-baseweb="tabs"] > [data-baseweb="tab-list"],
    [data-baseweb="tabs"] > div:has([data-baseweb="tab-list"]),
    [data-baseweb="tabs"] > [data-baseweb="tab-list"] {
        position: sticky !important;
        top: calc(var(--sticky-top) + var(--hdr-h));
        z-index: 98;
        background-color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Supabase (safe fallback)
# ------------------------------------------------------------------
db_connected = False
supabase = None
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        db_connected = True
except Exception as e:
    st.sidebar.error(f"Supabase Connection Warning: {e}")

# Kaggle backend: should expose POST /generate-voice that runs voice_engine.generate_xtts_voice
KAGGLE_URL = st.secrets.get("KAGGLE_BACKEND_URL", "https://canary-viscous-canned.ngrok-free.dev")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def save_message(role, content):
    if db_connected and supabase:
        try:
            supabase.table("chat_history").insert({"role": role, "content": content}).execute()
        except Exception:
            pass


def generate_voice_from_kaggle(text):
    try:
        r = requests.post(
            f"{KAGGLE_URL}/generate-voice",
            json={"text": text},
            headers={"ngrok-skip-browser-warning": "1"},
            timeout=30,
        )
        if r.status_code == 200 and len(r.content) > 100:
            return r.content
    except Exception as e:
        print(f"Kaggle Voice API Error: {e}")
    return None


def file_to_data_uri(candidates, fallback=""):
    mimes = {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    for path in candidates:
        if os.path.exists(path):
            ext = os.path.splitext(path)[1].lower()
            with open(path, "rb") as f:
                return f"data:{mimes.get(ext, 'image/png')};base64," + base64.b64encode(f.read()).decode()
    return fallback


def build_system_instruction(voice_mode=False):
    extra = "\nVoice mode: keep the reply under 40 words so it can be spoken in a few seconds." if voice_mode else ""
    return f"""
    You are Doraemon, the Central Master Multi-Agent Orchestrator for Rini's YouTube system.
    Currently viewing data context: {selected_channel} (ID: {current_channel_id}).
    Strict Core Metric: 1. Maximize Watch Time, 2. Viewer Satisfaction. Zero clickbait.
    Language Rule: Strictly reply in the exact same language/script the user used (Bangla if user speaks Bangla, English if user speaks English, Banglish if user speaks Banglish).
    Formatting Rule: Do NOT include any emotional action tags or brackets like [laughs], [waves excitedly], or [beeps happily]. Output clean plain text only.
    Always address her as Rini. Be friendly, warm, and act like a best friend.{extra}
    """


# ------------------------------------------------------------------
# Fully Fixed Animated Stage HTML/JS (GIF playback + Audio & Mouth Sync)
# ------------------------------------------------------------------
STAGE_HTML = """
<style>
  body{margin:0;background:transparent;font-family:sans-serif}
  .stage{height:380px;display:flex;flex-direction:column;align-items:center;justify-content:center;
         background:linear-gradient(#eaf6ff,#fff);border-radius:16px;border:1px solid #cfe6fb;position:relative}
  #dora{height:250px;width:250px;object-fit:contain;transform-origin:50% 100%;transition:0.2s}
  .idle #dora{animation:breathe 3s ease-in-out infinite}
  .talking #dora{animation:talk 0.4s ease-in-out infinite alternate}
  @keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.02)}}
  @keyframes talk{0%{transform:rotate(-3deg) translateY(0) scale(1.02)}100%{transform:rotate(3deg) translateY(-6px) scale(1.05)}}
  #status{margin-top:10px;color:#1f77b4;font-weight:700;font-size:15px}
  #play{display:none;margin-top:8px;padding:8px 18px;border:0;border-radius:20px;background:#ff4b4b;color:#fff;cursor:pointer;font-weight:bold}
  .rings{position:absolute;bottom:14px;display:flex;gap:4px;align-items:flex-end;height:26px}
  .rings i{width:5px;background:#1f77b4;border-radius:3px;height:4px;transition:height 0.1s}
</style>
<div class="stage idle" id="stage">
  <img id="dora" src="__GIF__">
  <div class="rings" id="bars"></div>
  <div id="status">Doraemon ready, Rini!</div>
  <button id="play">▶ Click to Hear Doraemon Voice</button>
</div>
<script>
const gifSrc = "__GIF__", staticSrc = "__STATIC__";
const audioSrc = "__AUDIO__", replyText = `__TEXT__`;
const stage = document.getElementById('stage'), img = document.getElementById('dora');
const status = document.getElementById('status'), playBtn = document.getElementById('play');
const barsEl = document.getElementById('bars');
const bars = []; for (let i=0;i<12;i++){const b=document.createElement('i');barsEl.appendChild(b);bars.push(b);}

function setTalking(on){
  stage.className = 'stage ' + (on ? 'talking' : 'idle');
  if(on){
    status.textContent='Doraemon kotha bolche... 🎙️';
    img.src = gifSrc;
  } else {
    status.textContent='Doraemon ready, Rini!';
    bars.forEach(b=>b.style.height='4px');
  }
}

function updateBars(active){
  bars.forEach(b=>{
    b.style.height = active ? (6 + Math.random()*22) + 'px' : '4px';
  });
}

if (audioSrc) {
  const audio = new Audio(audioSrc);
  const AC = window.AudioContext || window.webkitAudioContext;
  let ctx, analyser, source;
  
  function setupAudioAnalysis(){
    if(!ctx){
      ctx = new AC();
      analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source = ctx.createMediaElementSource(audio);
      source.connect(analyser);
      analyser.connect(ctx.destination);
    }
    const buf = new Uint8Array(analyser.frequencyBinCount);
    let raf;
    function loop(){
      analyser.getByteFrequencyData(buf);
      let sum = 0; for(let i=0; i<buf.length; i++) sum += buf[i];
      let avg = sum / buf.length;
      let isTalking = avg > 8;
      setTalking(isTalking);
      updateBars(isTalking);
      raf = requestAnimationFrame(loop);
    }
    audio.onplay = ()=>{ ctx.resume(); playBtn.style.display='none'; loop(); };
    audio.onended = ()=>{ cancelAnimationFrame(raf); setTalking(false); updateBars(false); };
  }

  setupAudioAnalysis();
  
  const startAudio = ()=>{
    audio.play().then(()=>{
      playBtn.style.display='none';
    }).catch(err=>{
      playBtn.style.display='inline-block';
    });
  };
  playBtn.onclick = startAudio;
  startAudio();
} else if (replyText && 'speechSynthesis' in window) {
  const u = new SpeechSynthesisUtterance(replyText);
  let t;
  u.onstart = ()=>{ setTalking(true); let o=false; t=setInterval(()=>{o=!o; updateBars(o);},150); };
  u.onend = ()=>{ clearInterval(t); setTalking(false); updateBars(false); };
  speechSynthesis.speak(u);
}
</script>
"""


def render_stage(reply=None, height=400):
    gif_uri = file_to_data_uri(["doraemon.gif"]) or "https://i.imgur.com/4AiXyZU.png"
    static = file_to_data_uri(["doraemon_closed.png", "doraemon.png"]) or gif_uri
    audio = reply["audio"] if reply and reply.get("audio") else ""
    text = reply["text"].replace("`", "'").replace("\\", "") if reply and not audio else ""
    
    html = (
        STAGE_HTML.replace("__GIF__", gif_uri)
        .replace("__STATIC__", static)
        .replace("__AUDIO__", audio)
        .replace("__TEXT__", text)
    )
    components.html(html, height=height)


# ------------------------------------------------------------------
# Sidebar Setup
# ------------------------------------------------------------------
channel_list = ["Default Channel"]
channel_dict = {}
if db_connected and supabase:
    try:
        res = supabase.table("channels").select("id, channel_name").execute()
        if res.data:
            channel_list = [ch["channel_name"] for ch in res.data]
            channel_dict = {ch["channel_name"]: ch["id"] for ch in res.data}
    except Exception:
        pass

st.sidebar.title("🤖 Doraemon MAS Engine")
selected_channel = st.sidebar.selectbox("📁 Select Channel Data View", channel_list)
current_channel_id = channel_dict.get(selected_channel, "general_room")

if db_connected:
    st.sidebar.success(f"✅ Data Sub-Room Active: {selected_channel}")
else:
    st.sidebar.warning("⚠️ Running in Offline UI Mode")

# ------------------------------------------------------------------
# Sticky Header Section (Core Mission Metric)
# ------------------------------------------------------------------
st.markdown(
    '<div class="mission-header">🎯 Core Mission Metric: Watch Time + Viewer Satisfaction 100% Guaranteed (Zero Clickbait)</div>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Chat history
# ------------------------------------------------------------------
if "central_chat_history" not in st.session_state:
    st.session_state.central_chat_history = []
    if db_connected and supabase:
        try:
            res = supabase.table("chat_history").select("*").order("created_at", desc=False).execute()
            if res.data:
                st.session_state.central_chat_history = [
                    {"role": row["role"], "content": row["content"]} for row in res.data
                ]
        except Exception:
            pass


# ------------------------------------------------------------------
# Voice popup: Talk with Doraemon
# ------------------------------------------------------------------
@st.dialog("🎙️ Talk with Doraemon", width="large")
def voice_dialog():
    stage_slot = st.container()
    st.caption("🎤 Start Talking: mic-e click koro. ■ Stop Talking: press kore thamao. Doraemon nijei reply dibe.")
    audio_value = st.audio_input("Start Talking / Stop Talking", key="voice_in")

    heard = None
    if audio_value is not None:
        data = audio_value.getvalue()
        digest = hashlib.md5(data).hexdigest()
        if st.session_state.get("voice_last") != digest:
            st.session_state.voice_last = digest
            with st.spinner("Doraemon sunche & Kaggle GPU voice generate korche..."):
                heard = transcribe_audio(data) or "Tomar kotha shunte peyechi, Rini."
                text, llm = call_master_brain(heard, build_system_instruction(voice_mode=True), fast=True)
                wav_bytes = generate_voice_from_kaggle(text)
                
                st.session_state.central_chat_history.append({"role": "user", "content": f"🎤 {heard}"})
                st.session_state.central_chat_history.append({"role": "assistant", "content": f"{text}\n\n*— Powered by: {llm}*"})
                save_message("user", f"🎤 {heard}")
                save_message("assistant", f"{text}\n\n*— Powered by: {llm}*")
                
                audio_uri = ""
                if wav_bytes:
                    audio_uri = "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode()
                
                st.session_state.voice_reply = {
                    "text": text,
                    "heard": heard,
                    "audio": audio_uri,
                }

    reply = st.session_state.get("voice_reply") if audio_value is not None else None
    with stage_slot:
        render_stage(reply)
        if reply:
            if reply.get("heard"):
                st.caption(f"Tumi bolle: {reply['heard']}")
            st.markdown(f"**Doraemon:** {reply['text']}")


# ------------------------------------------------------------------
# Chat input at main level
# ------------------------------------------------------------------
user_prompt = st.chat_input("Command Central Master Brain...")

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🧠 Central Master Doraemon Brain",
        "📊 Channels Overview",
        "📜 Scripts & Content Pipeline",
        "🎬 1-Click Approval Gate",
    ]
)

with tab1:
    st.subheader("🧠 Central Master Doraemon Brain Chat")

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("🎙️ Talk with Doraemon", type="primary", use_container_width=True):
            st.session_state.pop("voice_reply", None)
            st.session_state.pop("voice_last", None)
            voice_dialog()

    st.write("---")

    for message in st.session_state.central_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt:
        st.session_state.central_chat_history.append({"role": "user", "content": user_prompt})
        save_message("user", user_prompt)
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Master Brain processing & Kaggle XTTS voice generating..."):
                reply_text, active_llm = call_master_brain(user_prompt, build_system_instruction())
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                st.markdown(bot_reply)
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                save_message("assistant", bot_reply)

                wav_bytes = generate_voice_from_kaggle(reply_text)
                if wav_bytes:
                    b64_audio = base64.b64encode(wav_bytes).decode()
                    st.markdown(f'<audio controls autoplay src="data:audio/wav;base64,{b64_audio}"></audio>', unsafe_allow_html=True)
                else:
                    st.caption("🔊 Kaggle voice backend offline or generating...")

with tab2:
    st.subheader(f"Performance Metrics for: {selected_channel}")
    st.info("Channels table data view.")

with tab3:
    st.subheader(f"Content Pipeline Data ({selected_channel})")
    st.info("Scripts and content pipeline view.")

with tab4:
    st.subheader("Human-in-the-Loop Approval Gate")
    st.success("Videos generated by backend automation pause here for your review.")
