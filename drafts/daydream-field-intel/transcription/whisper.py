from pathlib import Path
from openai import OpenAI

SUPPORTED_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg", ".flac"}


def transcribe(audio_path: str) -> str:
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {path.suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}"
        )

    client = OpenAI()
    with open(path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )
    return transcript
