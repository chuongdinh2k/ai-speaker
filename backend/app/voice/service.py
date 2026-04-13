import uuid
import os
import asyncio
import boto3
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=boto3.session.Config(signature_version="s3v4"),
        )
    return _s3_client


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


async def upload_user_audio(audio_bytes: bytes, filename: str) -> str:
    """Upload raw user audio to S3 under user-audio/ prefix, return presigned URL."""
    ext = os.path.splitext(filename)[1] or ".webm"
    key = f"user-audio/{uuid.uuid4()}{ext}"
    content_type = _audio_content_type(ext)

    s3 = _get_s3_client()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=audio_bytes,
        ContentType=content_type,
    ))
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=settings.s3_presigned_url_expiry,
    )


async def synthesize_speech(text: str) -> str:
    """Generate TTS audio, upload to S3 under tts/ prefix, return pre-signed URL."""
    response = await client.audio.speech.create(model="tts-1", voice="alloy", input=text)
    key = f"tts/{uuid.uuid4()}.mp3"

    s3 = _get_s3_client()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: s3.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=response.content,
        ContentType="audio/mpeg",
    ))
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": key},
        ExpiresIn=settings.s3_presigned_url_expiry,
    )


def _audio_content_type(ext: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".mp4": "audio/mp4",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
    }.get(ext.lower(), "audio/webm")
