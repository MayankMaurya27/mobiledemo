# utils.py (sketch)
def speech_to_text(audio_path):
    # 1) open file
    # 2) send to speech recognition / whisper / STT provider
    # 3) return string transcript or None
    pass

def text_to_speech(text):
    # 1) call TTS provider (or locally use pyttsx3 or TTS service)
    # 2) save to file path (e.g., "reply.mp3")
    # 3) return path to file
    pass

def autoplay_audio(audio_file):
    # recommended: return an st.audio element or stream a bit
    # simplest: st.audio(audio_file, format='audio/mp3', start_time=0)
    pass
