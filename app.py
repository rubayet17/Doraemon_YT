import streamlit as st
import streamlit.components.v1 as components
import os
import requests
from supabase import create_client, Client

# Page Config
st.set_page_config(page_title="Doraemon MAS Control Hub", page_icon="🤖", layout="wide")

# Fixed Bottom Chat Input CSS Styling
st.markdown(
    """
    <style>
    [data-testid="stChatInput"] {
        position: fixed;
        bottom: 0;
        z-index: 100;
        background-color: white;
        padding-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Secrets & Supabase Init with Safe Fallback
db_connected = False
supabase = None
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        db_connected = True
except Exception as e:
    st.sidebar.error(f"Supabase Connection Warning: {e}")

# Kaggle Ngrok URL for Voice Generation
KAGGLE_URL = st.secrets.get("KAGGLE_BACKEND_URL", "https://canary-viscous-canned.ngrok-free.dev")

def generate_voice_from_kaggle(text):
    try:
        response = requests.post(f"{KAGGLE_URL}/generate-voice", json={"text": text}, timeout=15)
        if response.status_code == 200:
            audio_path = "temp_voice.wav"
            with open(audio_path, "wb") as f:
                f.write(response.content)
            return audio_path
    except Exception as e:
        print(f"Kaggle Voice API Error: {e}")
    return None

# Core Mission Header
st.markdown("### 🎯 Core Mission Metric: **Watch Time + Viewer Satisfaction 100% Guaranteed** (Zero Clickbait)")
st.write("---")

# Dynamic Channel Fetching
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

# Sidebar Channel Selector
st.sidebar.title("🤖 Doraemon MAS Engine")
selected_channel = st.sidebar.selectbox("📁 Select Channel Data View", channel_list)
current_channel_id = channel_dict.get(selected_channel, "general_room")

if db_connected:
    st.sidebar.success(f"✅ Data Sub-Room Active: {selected_channel}")
else:
    st.sidebar.warning("⚠️ Running in Offline UI Mode")

# Visual Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Central Master Doraemon Brain", 
    "📊 Channels Overview", 
    "📜 Scripts & Content Pipeline", 
    "🎬 1-Click Approval Gate"
])

with tab1:
    st.subheader("🧠 Central Master Doraemon Brain Chat")

    # Custom HTML/JS Component for Live Mic & Animated Doraemon State
    doraemon_mic_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: transparent;
                text-align: center;
                margin: 0;
                padding: 10px;
            }
            .card {
                background: #f0f8ff;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                max-width: 500px;
                margin: auto;
                border: 2px solid #1f77b4;
                display: flex;
                align-items: center;
                justify-content: space-around;
            }
            .img-container img {
                width: 150px;
                height: 150px;
                border-radius: 50%;
                object-fit: cover;
                border: 4px solid #1f77b4;
                transition: 0.3s;
            }
            .info-box {
                text-align: left;
                max-width: 260px;
            }
            .status {
                font-weight: bold;
                color: #333;
                margin-top: 10px;
                font-size: 14px;
            }
            .mic-btn {
                background-color: #ff4b4b;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 15px;
                cursor: pointer;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                margin-top: 12px;
                transition: 0.2s;
            }
            .mic-btn:hover {
                background-color: #e03e3e;
            }
            .mic-btn.recording {
                background-color: #28a745;
            }
        </style>
    </head>
    <body>

    <div class="card">
        <div class="img-container">
            <img id="doraemonImg" src="https://i.imgur.com/4AiXyZU.png" alt="Doraemon">
        </div>
        <div class="info-box">
            <h3>🎙️ Doraemon Active</h3>
            <div class="status" id="statusText">Ami shonchi, Rini! Mic button click kore kotha bolo...</div>
            <button class="mic-btn" id="micBtn" onclick="toggleRecord()">🎤 Start Talking</button>
        </div>
    </div>

    <script>
        let recording = false;

        function toggleRecord() {
            const btn = document.getElementById("micBtn");
            const status = document.getElementById("statusText");
            const img = document.getElementById("doraemonImg");

            if (!recording) {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        recording = true;
                        btn.innerText = "🛑 Stop & Send";
                        btn.classList.add("recording");
                        status.innerText = "🎙️ Recording your voice, Rini...";
                        img.style.borderColor = "#28a745";
                    })
                    .catch(err => {
                        alert("Microphone permission required!");
                    });
            } else {
                recording = false;
                btn.innerText = "🎤 Start Talking";
                btn.classList.remove("recording");
                status.innerText = "✨ Processing & generating audio reply...";
                img.style.borderColor = "#ff4b4b";

                setTimeout(() => {
                    status.innerText = "Ami ekhon ready achhi, Rini!";
                }, 2000);
            }
        }
    </script>

    </body>
    </html>
    """
    
    # Render component in Streamlit tab1 safely
    components.html(doraemon_mic_html, height=220)
    
    st.write("---")

    # Load Chat History from Session State / Supabase
    if "central_chat_history" not in st.session_state:
        st.session_state.central_chat_history = []
        if db_connected and supabase:
            try:
                res = supabase.table("chat_history").select("*").order("created_at", desc=False).execute()
                if res.data:
                    st.session_state.central_chat_history = [{"role": row["role"], "content": row["content"]} for row in res.data]
            except Exception:
                pass

    # Display Chat History
    for message in st.session_state.central_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input placed correctly at the BOTTOM (Gemini Style)
    if user_prompt := st.chat_input("Command Central Master Brain..."):
        st.session_state.central_chat_history.append({"role": "user", "content": user_prompt})
        if db_connected and supabase:
            try:
                supabase.table("chat_history").insert({"role": "user", "content": user_prompt}).execute()
            except Exception:
                pass
        
        with st.chat_message("user"):
            st.markdown(user_prompt)

        bot_reply = f"Ami tomar kotha bujhechi, Rini! '{user_prompt}' niye kaj shuru korchi."

        with st.chat_message("assistant"):
            st.markdown(bot_reply)
            st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
            if db_connected and supabase:
                try:
                    supabase.table("chat_history").insert({"role": "assistant", "content": bot_reply}).execute()
                except Exception:
                    pass
            
            # Kaggle GPU Voice API Call
            audio_file = generate_voice_from_kaggle(bot_reply)
            if audio_file and os.path.exists(audio_file):
                st.audio(audio_file, format="audio/wav")
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
