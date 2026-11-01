import os
import torch
import scipy.io.wavfile as wavfile
from TTS.api import TTS

# 1. XTTS v2 Model Load (Coqui TTS)
@st.cache_resource if 'st' in globals() else lambda x: x()
def load_xtts_model():
    # GPU থাকলে cuda, না থাকলে cpu
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts

# XTTS দিয়ে ডোরেমনের ভয়েসে টেক্সটকে অডিও করা
def generate_doraemon_voice(text, output_path="doraemon_reply.wav", speaker_wav="doraemon_voice_sample.wav"):
    try:
        tts = load_xtts_model()
        # বাংলা/ইংরেজি ভাষার জন্য ভাষা কোড সিলেক্ট করা
        tts.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav, # ডোরেমনের ভয়েস স্যাম্পল ফাইল
            language="en" # বাংলা হলে "bn" দিতে পারো যদি সাপোর্টেড ভার্সন হয়
        )
        return output_path
    except Exception as e:
        print(f"XTTS Generation Error: {e}")
        return None
