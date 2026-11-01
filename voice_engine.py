import os
import torch
from TTS.api import TTS

# GPU চেক করা (Kaggle বা লোকাল জিপিইউ থাকলে 'cuda' ব্যবহার করবে)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ১. XTTS v2 Model Load (ডোরেমনের আসল ভয়েস ক্লোনিংয়ের জন্য)
@st.cache_resource if 'st' in globals() else lambda x: x()
def load_xtts_model():
    try:
        tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)
        return tts
    except Exception as e:
        print(f"XTTS Load Error: {e}")
        return None

def generate_xtts_voice(text, output_path="doraemon_xtts.wav", speaker_wav="doraemon_voice_sample.wav"):
    try:
        tts = load_xtts_model()
        if tts:
            tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,  # ডোরেমনের ৫-১০ সেকেন্ডের ভয়েস স্যাম্পল ফাইল
                language="en"             # বাংলা সাপোর্টেড না হলে en দিয়ে কাজ চালানো যায়
            )
            return output_path
    except Exception as e:
        print(f"XTTS Generation Error: {e}")
    return None


# ২. Bark Model Load (ইমোশনাল, হাসি ও ন্যাচারাল টোনের জন্য)
def generate_bark_voice(text, output_path="doraemon_bark.wav"):
    try:
        from transformers import AutoProcessor, AutoModelForTextToSpeech
        import scipy.io.wavfile as wavfile
        
        processor = AutoProcessor.from_pretrained("suno/bark-small")
        model = AutoModelForTextToSpeech.from_pretrained("suno/bark-small").to(DEVICE)
        
        # Bark-এ ইমোশন ট্যাগ যেমন [laughs] সরাসরি কাজ করে
        inputs = processor(text, voice_preset="v2/en_speaker_6").to(DEVICE)
        audio_array = model.generate(**inputs)
        audio_array = audio_array.cpu().numpy().squeeze()
        
        # সেভ করা
        sample_rate = model.config.sample_rate
        wavfile.write(output_path, sample_rate, audio_array)
        return output_path
    except Exception as e:
        print(f"Bark Generation Error: {e}")
        return None
