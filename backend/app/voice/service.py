import uuid
import os
import boto3
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
    """Generate TTS audio, upload to S3, return pre-signed URL (1-hour expiry)."""
    response = await client.audio.speech.create(model="tts-1", voice="alloy", input=text)
    filename = f"{uuid.uuid4()}.mp3"

    s3 = boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=filename,
        Body=response.content,
        ContentType="audio/mpeg",
    )
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": filename},
        ExpiresIn=settings.s3_presigned_url_expiry,
    )
    return presigned_url
