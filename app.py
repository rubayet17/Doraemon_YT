import streamlit as st
import os
import streamlit.components.v1 as components
from supabase import create_client, Client
from llm_engine import call_master_brain

# Safe Voice Engine Import
try:
    from voice_engine import generate_xtts_voice, generate_bark_voice
    voice_enabled = True
except Exception:
    voice_enabled = False

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

# Secrets & Supabase Init
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    db_connected = True
except Exception as e:
    db_connected = False
    st.sidebar.error(f"❌ Supabase Connection Error: {e}")

# Database-e text message save korar helper function
def save_message_to_db(role, content):
    if db_connected:
        try:
            supabase.table("chat_history").insert({"role": role, "content": content}).execute()
        except Exception as e:
            print(f"DB Save Error: {e}")

# Core Mission Header
st.markdown("### 🎯 Core Mission Metric: **Watch Time + Viewer Satisfaction 100% Guaranteed** (Zero Clickbait)")
st.write("---")

# Dynamic Channel Fetching
channel_list = ["Default Channel"]
channel_dict = {}

if db_connected:
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

    # Interactive Toggle State for Live Visual Component
    if "mic_active" not in st.session_state:
        st.session_state.mic_active = False

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🎤 Toggle Doraemon Live Visual"):
            st.session_state.mic_active = not st.session_state.mic_active

    # Custom HTML/JS Voice-Visual Component Integration
    if st.session_state.mic_active:
        doraemon_live_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #ffffff;
                    text-align: center;
                    margin: 0;
                    padding: 10px;
                }
                .container {
                    background: #f0f8ff;
                    border-radius: 15px;
                    padding: 15px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    max-width: 450px;
                    margin: auto;
                    border: 2px solid #1f77b4;
                }
                img {
                    width: 160px;
                    height: 160px;
                    border-radius: 50%;
                    object-fit: cover;
                    border: 4px solid #1f77b4;
                    transition: 0.3s;
                }
                .status {
                    font-weight: bold;
                    color: #333;
                    margin: 12px 0;
                    font-size: 15px;
                }
                button {
                    background-color: #ff4b4b;
                    color: white;
                    border: none;
                    padding: 10px 22px;
                    border-radius: 20px;
                    font-size: 15px;
                    cursor: pointer;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    transition: 0.2s;
                }
                button:hover {
                    background-color: #e03e3e;
                }
                button.recording {
                    background-color: #28a745;
                }
            </style>
        </head>
        <body>

        <div class="container">
            <h3>🤖 Doraemon Live Companion</h3>
            <img id="doraemonImg" src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMml3bjF3YnYxdmhucmxreWZueHZ5NW51OWUzdjV4bXZrdXVnMWJjayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/eaQ8g94e5eNlK/giphy.gif" alt="Doraemon">
            <div class="status" id="statusText">Ami shonchi, Rini! Start talking button click kore kotha bolo...</div>
            <button id="micBtn" onclick="toggleRecording()">🎤 Start Talking</button>
        </div>

        <script>
            let isRecording = false;

            function toggleRecording() {
                const btn = document.getElementById("micBtn");
                const status = document.getElementById("statusText");
                const img = document.getElementById("doraemonImg");

                if (!isRecording) {
                    navigator.mediaDevices.getUserMedia({ audio: true })
                        .then(stream => {
                            isRecording = true;
                            btn.innerText = "🛑 Stop & Send";
                            btn.classList.add("recording");
                            status.innerText = "🎙️ Recording your voice, Rini...";
                            img.style.borderColor = "#28a745";
                        })
                        .catch(err => {
                            alert("Microphone permission denied or not allowed in browser iframe view.");
                        });
                } else {
                    isRecording = false;
                    btn.innerText = "🎤 Start Talking";
                    btn.classList.remove("recording");
                    status.innerText = "✨ Doraemon is listening & processing reply...";
                    img.style.borderColor = "#ff4b4b";

                    setTimeout(() => {
                        status.innerText = "Ami ekhon ready achhi, Rini!";
                    }, 2500);
                }
            }
        </script>

        </body>
        </html>
        """
        components.html(doraemon_live_html, height=340)

    st.write("---")

    # Load Chat History from Supabase
    if "central_chat_history" not in st.session_state:
        st.session_state.central_chat_history = []
        if db_connected:
            try:
                res = supabase.table("chat_history").select("*").order("created_at", desc=False).execute()
                if res.data:
                    st.session_state.central_chat_history = [{"role": row["role"], "content": row["content"]} for row in res.data]
            except Exception:
                pass

    # Display Chat History first
    for message in st.session_state.central_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input placed correctly at the BOTTOM (Gemini Style)
    if user_prompt := st.chat_input("Command Central Master Brain..."):
        st.session_state.central_chat_history.append({"role": "user", "content": user_prompt})
        save_message_to_db("user", user_prompt)
        
        with st.chat_message("user"):
            st.markdown(user_prompt)

        system_instruction = f"""
        You are Doraemon, the Central Master Multi-Agent Orchestrator for Rini's YouTube system.
        Currently viewing data context: {selected_channel} (ID: {current_channel_id}).
        Strict Core Metric: 1. Maximize Watch Time, 2. Viewer Satisfaction. Zero clickbait.
        Language Rule: Strictly reply in the exact same language/script the user used (Bangla if user speaks Bangla, English if user speaks English, Banglish if user speaks Banglish).
        Formatting Rule: Do NOT include any emotional action tags or brackets like [laughs], [waves excitedly], or [beeps happily]. Output clean plain text only.
        Always address her as Rini. Be friendly, warm, and act like a best friend.
        """

        with st.chat_message("assistant"):
            with st.spinner("Master Brain processing..."):
                reply_text, active_llm = call_master_brain(user_prompt, system_instruction)
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                
                st.markdown(bot_reply)
                
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                save_message_to_db("assistant", bot_reply)
                
                # --- Voice Output Integration ---
                if voice_enabled:
                    try:
                        audio_path = generate_xtts_voice(reply_text)
                        if audio_path and os.path.exists(audio_path):
                            st.audio(audio_path, format="audio/wav", autoplay=True)
                    except Exception as ex:
                        st.caption(f"🔊 Voice note: {ex}")
                else:
                    st.caption("💡 Voice generation runs on backend.")

with tab2:
    st.subheader(f"Performance Metrics for: {selected_channel}")
    if db_connected:
        try:
            res = supabase.table("channels").select("*").eq("channel_name", selected_channel).execute()
            st.dataframe(res.data, use_container_width=True)
        except Exception:
            st.info("Channels table loading...")

with tab3:
    st.subheader(f"Content Pipeline Data ({selected_channel})")
    if db_connected:
        try:
            res = supabase.table("scripts_and_videos").select("*").eq("channel_id", current_channel_id).execute()
            if res.data:
                st.dataframe(res.data, use_container_width=True)
            else:
                st.info(f"No pipeline data found for {selected_channel} yet.")
        except Exception:
            st.info("Scripts table loading or filter pending...")

with tab4:
    st.subheader("Human-in-the-Loop Approval Gate")
    st.success("Videos generated by backend automation pause here for your review before publishing.")
