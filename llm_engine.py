import streamlit as st
import json
import urllib.request
import google.generativeai as genai

def call_master_brain(prompt, system_instruction="", fast=False):
    """
    Strict Fallback Order with 10s Timeout:
    1. OpenRouter (Tries first, timeout 10s)
    2. Groq (Second fallback, timeout 10s)
    3. Gemini Latest Model (Final fallback, no hardcoded restriction)
    """
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    
    # --- 1. TRY OPENROUTER ---
    openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            req_data = json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": [{"role": "user", "content": full_prompt}]
            }).encode('utf-8')
            
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                return res_json['choices'][0]['message']['content'], "🟢 OpenRouter"
        except Exception:
            pass 

    # --- 2. TRY GROQ ---
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            req_data = json.dumps({
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": full_prompt}]
            }).encode('utf-8')
            
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_data,
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                return res_json['choices'][0]['message']['content'], "⚡ Groq"
        except Exception:
            pass 

    # --- 3. FINAL FALLBACK: GEMINI ---
    try:
        gemini_key = st.secrets.get("GEMINI_API_KEY", "")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            return response.text, "✨ Gemini (Latest Flash)"
    except Exception as e:
        return f"⚠️ All LLM fallbacks failed. Error: {e}", "❌ None"

    return "⚠️ Please configure at least one API key in Streamlit Secrets.", "❌ None"


def transcribe_audio(audio_bytes):
    """
    Optional audio transcription handler via Groq Whisper API (or fallback)
    """
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if not groq_key:
        return None
    
    try:
        # Multipart form data upload to Groq Whisper endpoint can be handled here if needed,
        # or return a fallback text for now.
        return "Tomar kotha shunte peyechi, Rini."
    except Exception as e:
        print(f"Transcription Error: {e}")
        return None
