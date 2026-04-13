import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.models.user import User
from app.auth.service import pwd_context, create_access_token
from app.config import settings
from app.voice.service import synthesize_speech

async def seed_user(db_session):
    user = User(email=f"v{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_access_token(user)

@pytest.mark.asyncio
async def test_transcribe_requires_auth(client):
    resp = await client.post("/voice/transcribe")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_transcribe_returns_text(client, db_session):
    token = await seed_user(db_session)
    with patch("app.voice.service.client") as mock_openai:
        mock_openai.audio.transcriptions.create = AsyncMock(
            return_value=MagicMock(text="Hello world")
        )
        resp = await client.post(
            "/voice/transcribe",
            files={"file": ("audio.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello world"

def test_settings_has_s3_config():
    assert hasattr(settings, "aws_access_key_id")
    assert hasattr(settings, "aws_secret_access_key")
    assert hasattr(settings, "s3_bucket_name")
    assert hasattr(settings, "s3_region")
    assert hasattr(settings, "s3_presigned_url_expiry")
    assert settings.s3_presigned_url_expiry == 3600

@pytest.mark.asyncio
async def test_synthesize_speech_returns_presigned_url():
    fake_audio_bytes = b"fake-mp3-content"
    fake_presigned_url = "https://my-bucket.s3.us-east-1.amazonaws.com/abc123.mp3?X-Amz-Signature=fake"

    mock_tts_response = MagicMock()
    mock_tts_response.content = fake_audio_bytes

    mock_s3_client = MagicMock()
    mock_s3_client.put_object = MagicMock()
    mock_s3_client.generate_presigned_url = MagicMock(return_value=fake_presigned_url)

    with patch("app.voice.service.client") as mock_openai, \
         patch("app.voice.service._get_s3_client", return_value=mock_s3_client):
        mock_openai.audio.speech.create = AsyncMock(return_value=mock_tts_response)
        result = await synthesize_speech("Hello world")

    assert result == fake_presigned_url
    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args.kwargs
    assert call_kwargs["ContentType"] == "audio/mpeg"
    assert call_kwargs["Body"] == fake_audio_bytes
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": mock_s3_client.put_object.call_args.kwargs["Bucket"],
                "Key": mock_s3_client.put_object.call_args.kwargs["Key"]},
        ExpiresIn=settings.s3_presigned_url_expiry,
    )

@pytest.mark.asyncio
async def test_upload_user_audio_returns_presigned_url():
    from app.voice.service import upload_user_audio
    fake_url = "https://s3.example.com/user-audio/abc.webm?sig=x"
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()
    mock_s3.generate_presigned_url = MagicMock(return_value=fake_url)

    with patch("app.voice.service._get_s3_client", return_value=mock_s3):
        url = await upload_user_audio(b"fake audio bytes", "recording.webm")

    assert url == fake_url
    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Key"].startswith("user-audio/")
    assert call_kwargs["Key"].endswith(".webm")
    assert call_kwargs["ContentType"] == "audio/webm"

@pytest.mark.asyncio
async def test_synthesize_speech_uses_tts_prefix():
    from app.voice.service import synthesize_speech
    fake_url = "https://s3.example.com/tts/abc.mp3?sig=x"
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()
    mock_s3.generate_presigned_url = MagicMock(return_value=fake_url)
    mock_audio = MagicMock()
    mock_audio.content = b"mp3 bytes"

    with patch("app.voice.service._get_s3_client", return_value=mock_s3), \
         patch("app.voice.service.client") as mock_client:
        mock_client.audio.speech.create = AsyncMock(return_value=mock_audio)
        url = await synthesize_speech("Hello world")

    call_kwargs = mock_s3.put_object.call_args[1]
    assert call_kwargs["Key"].startswith("tts/")
    assert call_kwargs["Key"].endswith(".mp3")
