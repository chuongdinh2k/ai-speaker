# S3 Audio Pre-signed URLs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace local disk audio storage with S3, returning pre-signed URLs so only requests originating from the backend (authenticated chat flow) can play audio.

**Architecture:** `synthesize_speech` uploads MP3 bytes directly to S3 via boto3, immediately generates a 1-hour pre-signed URL, and returns it. The `/audio` StaticFiles mount is removed. No new endpoints are needed.

**Tech Stack:** Python, FastAPI, boto3 (AWS SDK), pytest, unittest.mock

---

## File Map

| File | Change |
|------|--------|
| `requirements.txt` | Add `boto3==1.34.69` |
| `app/config.py` | Add S3 settings, remove `audio_storage_path` |
| `app/voice/service.py` | Replace local file write with S3 upload + pre-sign |
| `app/main.py` | Remove `StaticFiles` mount for `/audio` |
| `tests/test_voice.py` | Add test for `synthesize_speech` with S3 mock |
| `.env` | Add AWS env vars (manual step, not committed) |

---

## Task 1: Add boto3 dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add boto3 to requirements.txt**

Open `requirements.txt` and add this line:

```
boto3==1.34.69
```

- [ ] **Step 2: Install the dependency**

```bash
pip install boto3==1.34.69
```

Expected output: `Successfully installed boto3-1.34.69 ...`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add boto3 dependency for S3 integration"
```

---

## Task 2: Update config to add S3 settings

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_voice.py`:

```python
def test_settings_has_s3_config():
    from app.config import settings
    assert hasattr(settings, "aws_access_key_id")
    assert hasattr(settings, "aws_secret_access_key")
    assert hasattr(settings, "s3_bucket_name")
    assert hasattr(settings, "s3_region")
    assert hasattr(settings, "s3_presigned_url_expiry")
    assert settings.s3_presigned_url_expiry == 3600
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_voice.py::test_settings_has_s3_config -v
```

Expected: FAIL with `AttributeError` or assertion error

- [ ] **Step 3: Update app/config.py**

Replace the entire file with:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    redis_url: str = "redis://localhost:6379"
    openai_api_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    rag_top_k: int = 5
    rag_recent_window: int = 10

    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    s3_region: str
    s3_presigned_url_expiry: int = 3600

settings = Settings()
```

- [ ] **Step 4: Add S3 vars to .env**

Add these lines to your `.env` file (not committed to git):

```
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
S3_BUCKET_NAME=your_bucket_name
S3_REGION=your_region
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_voice.py::test_settings_has_s3_config -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/config.py tests/test_voice.py
git commit -m "feat: add S3 configuration settings"
```

---

## Task 3: Replace local file write with S3 upload in synthesize_speech

**Files:**
- Modify: `app/voice/service.py`
- Modify: `tests/test_voice.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_voice.py`:

```python
@pytest.mark.asyncio
async def test_synthesize_speech_returns_presigned_url():
    from app.voice.service import synthesize_speech
    from unittest.mock import AsyncMock, patch, MagicMock

    fake_audio_bytes = b"fake-mp3-content"
    fake_presigned_url = "https://my-bucket.s3.us-east-1.amazonaws.com/abc123.mp3?X-Amz-Signature=fake"

    mock_tts_response = MagicMock()
    mock_tts_response.content = fake_audio_bytes

    mock_s3_client = MagicMock()
    mock_s3_client.put_object = MagicMock()
    mock_s3_client.generate_presigned_url = MagicMock(return_value=fake_presigned_url)

    with patch("app.voice.service.client") as mock_openai, \
         patch("app.voice.service.boto3.client", return_value=mock_s3_client):
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
        ExpiresIn=3600,
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_voice.py::test_synthesize_speech_returns_presigned_url -v
```

Expected: FAIL — `synthesize_speech` still writes to local disk

- [ ] **Step 3: Update app/voice/service.py**

Replace the entire file with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_voice.py::test_synthesize_speech_returns_presigned_url -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest tests/ -v
```

Expected: All previously passing tests still pass

- [ ] **Step 6: Commit**

```bash
git add app/voice/service.py tests/test_voice.py
git commit -m "feat: upload TTS audio to S3 and return pre-signed URL"
```

---

## Task 4: Remove the /audio StaticFiles mount

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update app/main.py**

Remove the `StaticFiles` import, the `os.makedirs` call, and the `app.mount` line. Replace the entire file with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
from app.voice.router import router as voice_router
from app.chat.router import router as chat_router
from app.admin.router import router as admin_router

app = FastAPI(title="AI Speaker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: remove local /audio static file mount"
```

---

## Task 5: Verify end-to-end manually

- [ ] **Step 1: Start the server**

```bash
uvicorn app.main:app --reload
```

- [ ] **Step 2: Get an auth token**

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' | python3 -m json.tool
```

Copy the `access_token` from the response.

- [ ] **Step 3: Send a chat message with voice reply**

```bash
curl -s -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "<a_valid_conversation_id>", "text": "Hello", "reply_with_voice": true}' \
  | python3 -m json.tool
```

Expected: Response contains `"audio_url": "https://..."` pointing to S3 (not `/audio/...`)

- [ ] **Step 4: Verify the pre-signed URL works**

```bash
curl -I "<the_audio_url_from_step_3>"
```

Expected: HTTP 200 with `Content-Type: audio/mpeg`

- [ ] **Step 5: Verify a random S3 URL is blocked**

```bash
curl -I "https://<your-bucket>.s3.<region>.amazonaws.com/nonexistent.mp3"
```

Expected: HTTP 403 Forbidden — bucket is private
