import os
import torch
from TTS.api import TTS

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

@st.cache_resource if 'st' in globals() else lambda x: x()
def load_xtts_model():
    try:
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)
        return tts
    except Exception as e:
        print(f"XTTS Load Error: {e}")
        return None

def generate_xtts_voice(text, output_path="doraemon_xtts.wav"):
    try:
        tts = load_xtts_model()
        if not tts:
            return None

        lower_text = text.lower()
        
        # Ekhane text analyze kore voice_samples folder theke sothik .wav file select korbe:
        if any(w in lower_text for w in ["haha", "hehe", "lol", "hasi", "fun", "mast"]):
            speaker_wav = "voice_samples/doraemon-laughing.wav"
        elif any(w in lower_text for w in ["kanna", "sad", "dukkhu", "cry", "sorry"]):
            speaker_wav = "voice_samples/doraemon-crying.wav"
        elif any(w in lower_text for w in ["rge", "pagol", "faltu", "angry"]):
            speaker_wav = "voice_samples/doraemon-angry.wav"
        elif any(w in lower_text for w in ["fear", "bhoy", "dar"]):
            speaker_wav = "voice_samples/doraemon-fear.wav"
        elif any(w in lower_text for w in ["gadget", "pocket", "kholo"]):
            speaker_wav = "voice_samples/doraemon-opening-gadget.wav"
        else:
            speaker_wav = "voice_samples/doraemon-default.wav"

        # Jodi kono karone specific file na paoa jay, tahole default file use korbe
        if not os.path.exists(speaker_wav):
            speaker_wav = "voice_samples/doraemon-default.wav"

        tts.tts_to_file(
            text=text,
            file_path=output_path,
            speaker_wav=speaker_wav,
            language="en"
        )
        return output_path
    except Exception as e:
        print(f"XTTS Generation Error: {e}")
        return None
