import whisper
import os

# Config: path to data folder
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")

def transcribe_audio(mp3_path):
    model = whisper.load_model("base")  # or "small", "medium", "large"
    audio_path = os.path.join(DATA_FOLDER, mp3_path)
    result = model.transcribe(audio_path)
    print("📝 Transcription:")
    print(result["text"])
    return result["text"]

# Example usage
transcribe_audio("extracted_audio.mp3")
