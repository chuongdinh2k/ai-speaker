import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.models.user import User
from app.models.topic import Topic
from app.models.conversation import Conversation
from app.auth.service import pwd_context, create_access_token

async def seed_conversation(db_session):
    user = User(email=f"chat{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name="Test Topic", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    return user, conv, create_access_token(user)

@pytest.mark.asyncio
async def test_rag_build_messages_deduplicates():
    from app.chat.rag import build_messages
    semantic = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    recent = [{"role": "user", "content": "hello"}]  # duplicate
    result = await build_messages("You are helpful.", semantic, recent, "new question")
    contents = [m["content"] for m in result]
    assert contents.count("hello") == 1
    assert result[0]["role"] == "system"
    assert result[-1]["content"] == "new question"

@pytest.mark.asyncio
async def test_handle_chat_message_text(db_session):
    from app.chat.service import handle_chat_message
    user = User(email=f"svc{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name="Svc Topic", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    with patch("app.chat.rag.openai_client") as mock_emb, \
         patch("app.chat.service.openai_client") as mock_llm:
        mock_emb.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        mock_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="The answer is 42."))])
        )
        result = await handle_chat_message(db_session, mock_redis, conv.id, "What is the answer?", None, "audio.webm", False)

    assert result["content"] == "The answer is 42."
    assert result["audio_url"] is None


@pytest.mark.asyncio
async def test_send_text_message_via_form(client, db_session):
    from app.auth.service import pwd_context, create_access_token
    from app.models.user import User
    from app.models.topic import Topic
    from app.models.conversation import Conversation

    user, conv, token = await seed_conversation(db_session)

    with patch("app.chat.service.openai_client") as mock_llm, \
         patch("app.chat.rag.openai_client") as mock_emb:
        mock_emb.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        mock_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Hi there!"))])
        )
        with patch("app.chat.router.get_redis", return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock())):
            resp = await client.post(
                "/chat/send",
                data={"conversation_id": str(conv.id), "content": "Hello", "reply_with_voice": "false"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["assistant_message"]["content"] == "Hi there!"
    assert body["user_message"]["audio_url"] is None


@pytest.mark.asyncio
async def test_send_audio_message_stores_audio_url(client, db_session):
    user, conv, token = await seed_conversation(db_session)
    fake_audio = b"fake webm bytes"
    fake_user_audio_url = "https://s3.example.com/user-audio/xyz.webm?sig=1"

    with patch("app.chat.service.openai_client") as mock_llm, \
         patch("app.chat.rag.openai_client") as mock_emb, \
         patch("app.voice.service.client") as mock_voice_client, \
         patch("app.voice.service._get_s3_client") as mock_s3_factory:
        mock_emb.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        mock_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="Got it!"))])
        )
        mock_voice_client.audio.transcriptions.create = AsyncMock(
            return_value=MagicMock(text="Hello from audio")
        )
        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock()
        mock_s3.generate_presigned_url = MagicMock(return_value=fake_user_audio_url)
        mock_s3_factory.return_value = mock_s3

        with patch("app.chat.router.get_redis", return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock())):
            resp = await client.post(
                "/chat/send",
                data={"conversation_id": str(conv.id), "reply_with_voice": "false"},
                files={"audio": ("recording.webm", fake_audio, "audio/webm")},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_message"]["content"] == "Hello from audio"
    assert body["user_message"]["audio_url"] == fake_user_audio_url


@pytest.mark.asyncio
async def test_send_requires_content_or_audio(client, db_session):
    user, conv, token = await seed_conversation(db_session)
    resp = await client.post(
        "/chat/send",
        data={"conversation_id": str(conv.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_chat_history_paginated(client, db_session):
    from app.models.message import Message as MessageModel
    user, conv, token = await seed_conversation(db_session)

    # Seed 15 messages
    for i in range(15):
        db_session.add(MessageModel(
            conversation_id=conv.id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"message {i}",
        ))
    await db_session.commit()

    # First page — no cursor
    resp = await client.get(
        f"/chat/{conv.id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 10
    assert body["next_cursor"] is not None
    # Messages should be oldest→newest within the page
    dates = [m["created_at"] for m in body["messages"]]
    assert dates == sorted(dates)

    # Second page — use cursor
    cursor = body["next_cursor"]
    resp2 = await client.get(
        f"/chat/{conv.id}/messages?cursor={cursor}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["messages"]) == 5
    assert body2["next_cursor"] is None


@pytest.mark.asyncio
async def test_get_system_prompt_injects_level_instruction(db_session):
    """Level instruction appears in the returned prompt."""
    from app.chat.rag import get_system_prompt
    from app.models.user import User
    from app.models.topic import Topic
    from app.models.conversation import Conversation
    from app.auth.service import pwd_context
    from uuid import uuid4

    user = User(email=f"lvl{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user", level="A1")
    topic = Topic(name="Level Topic", system_prompt="You are a language tutor.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    prompt = await get_system_prompt(
        db_session, conv.id, mock_redis,
        user_id=user.id,
        topic_id=topic.id,
        user_level="A1",
    )
    assert "very simple words" in prompt
    assert "very short sentences" in prompt


@pytest.mark.asyncio
async def test_get_system_prompt_different_levels_produce_different_prompts(db_session):
    """A1 and C2 produce distinct prompt content."""
    from app.chat.rag import get_system_prompt
    from app.models.user import User
    from app.models.topic import Topic
    from app.models.conversation import Conversation
    from app.auth.service import pwd_context
    from uuid import uuid4

    async def make_conv(level):
        user = User(email=f"lvl{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user", level=level)
        topic = Topic(name=f"Topic {level}", system_prompt="You are a language tutor.")
        db_session.add(user)
        db_session.add(topic)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(topic)
        conv = Conversation(user_id=user.id, topic_id=topic.id)
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)
        return user, conv

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    user_a1, conv_a1 = await make_conv("A1")
    user_c2, conv_c2 = await make_conv("C2")

    prompt_a1 = await get_system_prompt(db_session, conv_a1.id, mock_redis, user_id=user_a1.id, topic_id=conv_a1.topic_id, user_level="A1")
    prompt_c2 = await get_system_prompt(db_session, conv_c2.id, mock_redis, user_id=user_c2.id, topic_id=conv_c2.topic_id, user_level="C2")

    assert prompt_a1 != prompt_c2
    assert "deep reflection" in prompt_c2


@pytest.mark.asyncio
async def test_get_system_prompt_no_level_omits_level_block(db_session):
    """When user_level is None, no level instruction is injected."""
    from app.chat.rag import get_system_prompt
    from app.models.user import User
    from app.models.topic import Topic
    from app.models.conversation import Conversation
    from app.auth.service import pwd_context
    from uuid import uuid4

    user = User(email=f"nolvl{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user", level="A2")
    topic = Topic(name="No Level Topic", system_prompt="You are a tutor.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    prompt = await get_system_prompt(
        db_session, conv.id, mock_redis,
        user_id=user.id,
        topic_id=topic.id,
        user_level=None,
    )
    # No level-specific text
    assert "very simple words" not in prompt
    assert "deep reflection" not in prompt
