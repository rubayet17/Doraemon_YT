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

    # Clean, Native Streamlit Layout (No broken HTML/JS iframes)
    col_v1, col_v2 = st.columns([1, 2])
    
    with col_v1:
        # Local doraemon.gif file display
        if os.path.exists("doraemon.gif"):
            st.image("doraemon.gif", width=220)
        else:
            st.image("https://i.imgur.com/4AiXyZU.png", width=220)
            
    with col_v2:
        st.markdown("### 🎙️ Doraemon Master Brain Active")
        st.success("Ami ekhon shob bujhe felechi, Rini! Niche mic-e click kore kotha bolo ba chat box-e command dao—ami Kaggle GPU diye voice reply pathacchi!")
        
        # Native Streamlit Audio Input (100% Reliable Mic Recording)
        audio_value = st.audio_input("🎤 Record Voice Note for Doraemon")
        if audio_value:
            st.info("Audio recorded successfully! Processing through Master Brain...")
            # Ekhane audio file-ke backend-e pathanor ba text-e convert korar logic add kora jabe

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

        system_instruction = f"""
        You are Doraemon, the Central Master Multi-Agent Orchestrator for Rini's YouTube system.
        Currently viewing data context: {selected_channel} (ID: {current_channel_id}).
        Strict Core Metric: 1. Maximize Watch Time, 2. Viewer Satisfaction. Zero clickbait.
        Language Rule: Strictly reply in the exact same language/script the user used (Bangla if user speaks Bangla, English if user speaks English, Banglish if user speaks Banglish).
        Formatting Rule: Do NOT include any emotional action tags or brackets like [laughs], [waves excitedly], or [beeps happily]. Output clean plain text only.
        Always address her as Rini. Be friendly, warm, and act like a best friend.
        """

        with st.chat_message("assistant"):
            with st.spinner("Master Brain processing & generating Kaggle GPU voice..."):
                reply_text, active_llm = call_master_brain(user_prompt, system_instruction)
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                
                st.markdown(bot_reply)
                
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                if db_connected and supabase:
                    try:
                        supabase.table("chat_history").insert({"role": "assistant", "content": bot_reply}).execute()
                    except Exception:
                        pass
                
                # --- Kaggle GPU Voice API Integration ---
                audio_file = generate_voice_from_kaggle(reply_text)
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
