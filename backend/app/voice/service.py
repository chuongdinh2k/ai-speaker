import uuid
import os
import base64
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio bytes to Whisper STT, return transcribed text."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            transcript = await client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcript.text
    finally:
        os.unlink(tmp_path)

async def synthesize_speech(text: str) -> str:
    """Generate TTS audio, save to storage, return relative URL path."""
    response = await client.audio.speech.create(model="tts-1", voice="alloy", input=text)
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(settings.audio_storage_path, filename)
    with open(filepath, "wb") as f:
        f.write(response.content)
    return f"/audio/{filename}"
