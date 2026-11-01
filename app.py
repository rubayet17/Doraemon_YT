import streamlit as st
import os
from supabase import create_client, Client
from llm_engine import call_master_brain
from voice_engine import generate_xtts_voice, generate_bark_voice

# Page Config
st.set_page_config(page_title="Doraemon MAS Control Hub", page_icon="🤖", layout="wide")

# Secrets & Supabase Init
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    db_connected = True
except Exception as e:
    db_connected = False
    st.sidebar.error(f"❌ Supabase Connection Error: {e}")

# Database-e message save korar helper function
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
    st.write("Kotha hobe ekdom Central Master Brain-er sathe. Apni je kono channel-er byapare ekhane command dite parben.")

    # Visual Doraemon Animated Avatar Display
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3Z2anJ5OGZ3czJ4N255bnF3bmJ1bWF3aXZ5OTN5MXI2Zm56eXBwciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3ohhwkKBc99HUgjAP6/giphy.gif", width=120)
    with col2:
        st.info("🤖 **Doraemon Status:** Online & Ready to chat with emotional voice clone, Rini!")

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
        
        if not st.session_state.central_chat_history:
            default_welcome = "Namaskar Rini! Ami Doraemon, apnar Central Master Brain. Bolun, ajke kon channel-er ki kaj korbo?"
            st.session_state.central_chat_history = [{"role": "assistant", "content": default_welcome}]
            save_message_to_db("assistant", default_welcome)

    for message in st.session_state.central_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("Command Central Master Brain..."):
        st.session_state.central_chat_history.append({"role": "user", "content": user_prompt})
        save_message_to_db("user", user_prompt)
        
        with st.chat_message("user"):
            st.markdown(user_prompt)

        system_instruction = f"""
        You are Doraemon, the Central Master Multi-Agent Orchestrator for Rini's YouTube system.
        Currently viewing data context: {selected_channel} (ID: {current_channel_id}).
        Strict Core Metric: 1. Maximize Watch Time, 2. Viewer Satisfaction. Zero clickbait.
        Be conversational, active, and helpful like a best friend. Always address her as Rini. Include emotional cues like [laughs] where natural.
        """

        with st.chat_message("assistant"):
            with st.spinner("Master Brain processing & generating emotional voice..."):
                reply_text, active_llm = call_master_brain(user_prompt, system_instruction)
                bot_reply = f"{reply_text}\n\n*— Powered by: {active_llm}*"
                
                st.markdown(bot_reply)
                
                st.session_state.central_chat_history.append({"role": "assistant", "content": bot_reply})
                save_message_to_db("assistant", bot_reply)
                
                # --- Voice Output Integration (XTTS / Bark) ---
                try:
                    # তুমি চাইলে generate_xtts_voice বা generate_bark_voice ব্যবহার করতে পারো
                    audio_path = generate_xtts_voice(reply_text)
                    if audio_path and os.path.exists(audio_path):
                        st.audio(audio_path, format="audio/wav", autoplay=True)
                except Exception as ex:
                    st.caption(f"🔊 Voice generation note: {ex}")

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
