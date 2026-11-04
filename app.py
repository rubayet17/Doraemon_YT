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
            timeout=20,
        )
        if r.status_code == 200:
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


@st.cache_data
def gif_first_frame_uri(path="doraemon.gif"):
    """Still first frame of the gif, used while Doraemon is idle."""
    try:
        from PIL import Image

        im = Image.open(path)
        im.seek(0)
        buf = io.BytesIO()
        im.convert("RGBA").save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


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
# Animated stage (runs in the browser)
#  - idle:    still first frame of doraemon.gif, gentle breathing
#  - talking: doraemon.gif plays (hand/body movement) + body sways with voice volume
#  - optional: doraemon_closed.png / doraemon_open.png -> real mouth swap by volume
# ------------------------------------------------------------------
STAGE_HTML = """
<style>
  body{margin:0;background:transparent;font-family:sans-serif}
  .stage{height:380px;display:flex;flex-direction:column;align-items:center;justify-content:center;
         background:linear-gradient(#eaf6ff,#fff);border-radius:16px;border:1px solid #cfe6fb;position:relative}
  #dora{height:270px;transform-origin:50% 100%}
  .idle #dora{animation:breathe 3s ease-in-out infinite}
  .talking #dora{animation:talk .45s ease-in-out infinite alternate}
  @keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.015)}}
  @keyframes talk{0%{transform:rotate(-2.5deg) translateY(0)}100%{transform:rotate(2.5deg) translateY(-8px)}}
  #status{margin-top:10px;color:#2a6fb0;font-weight:600}
  #play{display:none;margin-top:6px;padding:6px 14px;border:0;border-radius:20px;background:#e8453c;color:#fff;cursor:pointer}
  .rings{position:absolute;bottom:14px;display:flex;gap:4px;align-items:flex-end;height:26px}
  .rings i{width:5px;background:#4aa3e8;border-radius:3px;height:4px}
</style>
<div class="stage idle" id="stage">
  <img id="dora" src="__STATIC__">
  <div class="rings" id="bars"></div>
  <div id="status">Doraemon ready, Rini!</div>
  <button id="play">▶ Tap to hear reply</button>
</div>
<script>
const staticSrc = "__STATIC__", gifSrc = "__GIF__", openSrc = "__OPEN__";
const audioSrc = "__AUDIO__", replyText = `__TEXT__`;
const stage = document.getElementById('stage'), img = document.getElementById('dora');
const status = document.getElementById('status'), playBtn = document.getElementById('play');
const barsEl = document.getElementById('bars');
const bars = []; for (let i=0;i<14;i++){const b=document.createElement('i');barsEl.appendChild(b);bars.push(b);}

function setTalking(on){
  stage.className = 'stage ' + (on ? 'talking' : 'idle');
  if(on){ status.textContent='Doraemon bolche...'; if(!openSrc && gifSrc) img.src = gifSrc + '#' + Date.now(); }
  else { img.src = staticSrc; bars.forEach(b=>b.style.height='4px'); status.textContent='Doraemon ready, Rini!'; }
}
function mouth(open, level){
  if(openSrc) img.src = open ? openSrc : staticSrc;
  bars.forEach(b=>{ b.style.height = (4 + (open ? Math.random()*level*40 : 0)) + 'px'; });
}

if (audioSrc) {
  const audio = new Audio(audioSrc);
  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC();
  const analyser = ctx.createAnalyser(); analyser.fftSize = 512;
  ctx.createMediaElementSource(audio).connect(analyser); analyser.connect(ctx.destination);
  const buf = new Uint8Array(analyser.fftSize);
  let raf;
  function loop(){
    analyser.getByteTimeDomainData(buf);
    let s=0; for(const v of buf){const d=(v-128)/128; s+=d*d;}
    const rms = Math.sqrt(s/buf.length);
    mouth(rms > 0.04, rms*3);
    raf = requestAnimationFrame(loop);
  }
  audio.onplay = ()=>{ setTalking(true); loop(); playBtn.style.display='none'; };
  audio.onended = ()=>{ cancelAnimationFrame(raf); setTalking(false); };
  const start = ()=>{ ctx.resume(); audio.play().catch(()=>{ playBtn.style.display='inline-block'; }); };
  playBtn.onclick = start;
  start();
} else if (replyText && 'speechSynthesis' in window) {
  // Fallback when Kaggle voice is offline: browser voice + timer-driven mouth
  const u = new SpeechSynthesisUtterance(replyText);
  let t;
  u.onstart = ()=>{ setTalking(true); let o=false; t=setInterval(()=>{o=!o;mouth(o,0.5);},140); };
  u.onend = ()=>{ clearInterval(t); setTalking(false); };
  speechSynthesis.speak(u);
}
</script>
"""


def render_stage(reply=None, height=400):
    gif_uri = file_to_data_uri(["doraemon.gif"])
    static = (
        file_to_data_uri(["doraemon_closed.png", "doraemon.png"])
        or gif_first_frame_uri("doraemon.gif")
        or gif_uri
        or "https://i.imgur.com/4AiXyZU.png"
    )
    opened = file_to_data_uri(["doraemon_open.png"], "")
    audio = reply["audio"] if reply and reply.get("audio") else ""
    text = reply["text"].replace("`", "'").replace("\\", "") if reply and not audio else ""
    html = (
        STAGE_HTML.replace("__STATIC__", static)
        .replace("__GIF__", gif_uri)
        .replace("__OPEN__", opened)
        .replace("__AUDIO__", audio)
        .replace("__TEXT__", text)
    )
    components.html(html, height=height)


# ------------------------------------------------------------------
# Sidebar
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

st.markdown("### 🎯 Core Mission Metric: **Watch Time + Viewer Satisfaction 100% Guaranteed** (Zero Clickbait)")
st.write("---")

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
#   mic -> Whisper (Groq) -> call_master_brain (OpenRouter/Groq/Gemini) -> Kaggle XTTS voice
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
            with st.spinner("Doraemon sunche..."):
                heard = transcribe_audio(data)
                if not heard:
                    st.session_state.voice_reply = {"text": "Ami thik bujhte parlam na, Rini. Abar bolo na!", "audio": "", "heard": ""}
                else:
                    text, llm = call_master_brain(heard, build_system_instruction(voice_mode=True), fast=True)
                    wav = generate_voice_from_kaggle(text)
                    st.session_state.central_chat_history.append({"role": "user", "content": f"🎤 {heard}"})
                    st.session_state.central_chat_history.append({"role": "assistant", "content": f"{text}\n\n*— Powered by: {llm}*"})
                    save_message("user", f"🎤 {heard}")
                    save_message("assistant", f"{text}\n\n*— Powered by: {llm}*")
                    st.session_state.voice_reply = {
                        "text": text,
                        "heard": heard,
                        "audio": ("data:audio/wav;base64," + base64.b64encode(wav).decode()) if wav else "",
                    }

    reply = st.session_state.get("voice_reply") if audio_value is not None else None
    with stage_slot:
        render_stage(reply)
        if reply:
            if reply.get("heard"):
                st.caption(f"Tumi bolle: {reply['heard']}")
            st.markdown(f"**Doraemon:** {reply['text']}")


# ------------------------------------------------------------------
# Chat input at main level -> Streamlit pins it to the bottom automatically
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
            with st.spinner("Master Brain processing..."):
                reply_text, active_llm = call_master_brain(user_prompt, build_system_instruction())
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                st.markdown(bot_reply)
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                save_message("assistant", bot_reply)

                wav = generate_voice_from_kaggle(reply_text)
                if wav:
                    st.audio(wav, format="audio/wav")
                else:
                    st.caption("🔊 Voice generation running or backend offline.")

with tab2:
    st.subheader(f"Performance Metrics for: {selected_channel}")
    st.info("Channels table data view.")

with tab3:
    st.subheader(f"Content Pipeline Data ({selected_channel})")
    st.info("Scripts and content pipeline view.")

with tab4:
    st.subheader("Human-in-the-Loop Approval Gate")
    st.success("Videos generated by backend automation pause here for your review.")
