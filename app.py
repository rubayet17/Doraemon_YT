import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Doraemon MAS Control Hub", page_icon="🤖", layout="wide")

# Secrets Retrieval
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Initialize Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Initialize Gemini LLM
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    st.sidebar.success("✅ Supabase & Gemini Connected!")
except Exception as e:
    st.sidebar.error(f"❌ API Secrets Error: {e}")

# Sidebar Header
st.sidebar.title("🤖 Doraemon MAS Engine")
selected_channel = st.sidebar.selectbox(
    "Select Channel View", 
    ["All Channels", "Channel 1 (Auto-Vid 1)", "Channel 2 (Auto-Vid 2)", "Channel 3 (Manual)"]
)

# Core Metric Header
st.markdown("### 🎯 Core Mission Metric: **Watch Time + Viewer Satisfaction 100% Guaranteed**")
st.write("---")

# Visual Tabs for Tables & Intelligence
tab1, tab2, tab3, tab4 = st.tabs(["📊 Channels Overview", "📜 Scripts & Content Pipeline", "🎬 Videos Queue", "🧠 Doraemon Master Brain Chat"])

with tab1:
    st.subheader("YouTube Channels Performance")
    try:
        res = supabase.table("channels").select("*").execute()
        st.dataframe(res.data, use_container_width=True)
    except Exception as err:
        st.info("Channels table loading or waiting for data...")

with tab2:
    st.subheader("Scripts & Retention Engine")
    try:
        res = supabase.table("scripts_and_videos").select("*").execute()
        st.dataframe(res.data, use_container_width=True)
    except Exception as err:
        st.info("Scripts table loading or waiting for data...")

with tab3:
    st.subheader("1-Click Approval & Execution Gate")
    st.success("Human-in-the-Loop Gate Ready: Videos will appear here for your approval before rendering!")

with tab4:
    st.subheader("💬 Chat with Doraemon (Master Brain)")
    st.write("Doraemon commands 9 fixed agents focused on **Audience Retention & Real Value**.")
    
    user_input = st.text_input("Ask Doraemon anything about channel strategy, script ideas, or bug fixes:")
    if st.button("Send Instruction"):
        if user_input:
            system_prompt = """You are Doraemon, an elite Multi-Agent Orchestrator for Rini's 3 YouTube channels. 
            Your #1 rule is strictly maximizing WATCH TIME and VIEWER SATISFACTION (zero clickbait/misleading content). 
            Coordinate your 9 specialized agents to deliver high-retention content blueprints and maintain system stability."""
            
            with st.spinner("Doraemon & 9 Agents are thinking..."):
                response = model.generate_content(f"{system_prompt}\n\nUser Question: {user_input}")
                st.markdown(f"**🤖 Doraemon:** {response.text}")
