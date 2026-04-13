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
