import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.models.user import User
from app.auth.service import pwd_context, create_access_token

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
        import io
        resp = await client.post(
            "/voice/transcribe",
            files={"file": ("audio.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello world"
