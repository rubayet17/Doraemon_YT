import streamlit as st
import os
import requests
from supabase import create_client, Client
from llm_engine import call_master_brain

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

# Kaggle Ngrok URL from Secrets for Voice Generation
KAGGLE_URL = st.secrets.get("KAGGLE_BACKEND_URL", "https://canary-viscous-canned.ngrok-free.dev")

def generate_voice_from_kaggle(text):
    try:
        response = requests.post(f"{KAGGLE_URL}/generate-voice", json={"text": text}, timeout=45)
        if response.status_code == 200:
            audio_path = "temp_voice.wav"
            with open(audio_path, "wb") as f:
                f.write(response.content)
            return audio_path
    except Exception as e:
        print(f"Kaggle Voice API Error: {e}")
    return None

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

    # Local repository-er doraemon.gif file direct use kora holo
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.image("doraemon.gif", width=220)
    with col_v2:
        st.markdown("### 🎙️ Hello Rini!")
        st.info("Ami Tomar Master Brain Doraemon! Niche chat box-e kotha bolo ba audio record koro, ami Kaggle GPU diye voice reply pathacchi!")

    # Native Streamlit Audio Input (Direct Mic Recording)
    audio_value = st.audio_input("🎤 Click to Record Voice Note")
    if audio_value:
        st.success("Voice note received successfully! Processing through Master Brain...")
        # Ekhane audio file-ke backend-e pathanor logic ba text conversion add kora jabe

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

        system_image_instruction = f"""
        You are Doraemon, the Central Master Multi-Agent Orchestrator for Rini's YouTube system.
        Currently viewing data context: {selected_channel} (ID: {current_channel_id}).
        Strict Core Metric: 1. Maximize Watch Time, 2. Viewer Satisfaction. Zero clickbait.
        Language Rule: Strictly reply in the exact same language/script the user used (Bangla if user speaks Bangla, English if user speaks English, Banglish if user speaks Banglish).
        Formatting Rule: Do NOT include any emotional action tags or brackets like [laughs], [waves excitedly], or [beeps happily]. Output clean plain text only.
        Always address her as Rini. Be friendly, warm, and act like a best friend.
        """

        with st.chat_message("assistant"):
            with st.spinner("Master Brain processing & generating Kaggle GPU voice..."):
                reply_text, active_llm = call_master_brain(user_prompt, system_image_instruction)
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                
                st.markdown(bot_reply)
                
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                save_message_to_db("assistant", bot_reply)
                
                # --- Kaggle GPU Voice API Integration ---
                audio_file = generate_voice_from_kaggle(reply_text)
                if audio_file and os.path.exists(audio_file):
                    st.audio(audio_file, format="audio/wav", autoplay=True)
                else:
                    st.caption("🔊 Voice generation running or backend offline.")

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
