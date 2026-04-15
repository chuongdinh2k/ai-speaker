# Vocabulary System & AI Question Prompting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-user vocabulary system per topic with Redis-cached system prompt injection, usage tracking, and chat highlighting, plus AI question-asking behavior via system prompt instruction.

**Architecture:** New `user_vocabularies` table + `app/vocabularies/` module exposes CRUD + activate/deactivate endpoints. On chat, `get_system_prompt` reads/writes three Redis keys (`active_vocab`, `vocab_history`, `system_prompt_vocab`) with DB fallback, builds an enriched prompt with vocab context and question-asking instruction, and returns `active_vocab` in the chat response for client-side highlighting.

**Tech Stack:** FastAPI, SQLAlchemy (async), PostgreSQL, Redis (aioredis), Alembic, React + TypeScript, Tailwind CSS

---

## File Map

**Created:**
- `backend/app/models/vocabulary.py` — `UserVocabulary` SQLAlchemy model
- `backend/app/schemas/vocabulary.py` — Pydantic request/response schemas
- `backend/app/vocabularies/__init__.py` — empty
- `backend/app/vocabularies/service.py` — DB + Redis logic for vocab CRUD and caching
- `backend/app/vocabularies/router.py` — FastAPI router for `/vocabularies`
- `backend/alembic/versions/002_user_vocabularies.py` — migration
- `frontend/src/pages/VocabularyPage.tsx` — vocabulary management UI

**Modified:**
- `backend/app/main.py` — register vocabularies router
- `backend/app/chat/rag.py` — enrich `get_system_prompt` with vocab context
- `backend/app/chat/service.py` — pass `user_id`/`topic_id`, increment usage_count, return `active_vocab`
- `backend/app/chat/router.py` — pass `user_id` to `handle_chat_message`, include `active_vocab` in response
- `backend/app/schemas/chat.py` — add `active_vocab` field to `ChatSendResponse`
- `frontend/src/api/endpoints.ts` — add vocab API calls + updated `ChatSendResponse` type
- `frontend/src/components/MessageBubble.tsx` — highlight active vocab words in assistant messages
- `frontend/src/pages/ChatPage.tsx` — pass `active_vocab` to `MessageBubble`, load topic_id
- `frontend/src/pages/TopicsPage.tsx` — add "Vocabulary" link per topic card
- `frontend/src/App.tsx` — add `/topics/:topicId/vocabulary` route

---

## Task 1: DB Model + Alembic Migration

**Files:**
- Create: `backend/app/models/vocabulary.py`
- Create: `backend/alembic/versions/002_user_vocabularies.py`

- [ ] **Step 1: Create the SQLAlchemy model**

Create `backend/app/models/vocabulary.py`:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class UserVocabulary(Base):
    __tablename__ = "user_vocabularies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    word: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

- [ ] **Step 2: Create the Alembic migration**

Create `backend/alembic/versions/002_user_vocabularies.py`:

```python
"""add user_vocabularies table

Revision ID: 002
Revises: 001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'user_vocabularies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id'), nullable=False),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_user_vocabularies_user_topic', 'user_vocabularies', ['user_id', 'topic_id'])

def downgrade() -> None:
    op.drop_index('ix_user_vocabularies_user_topic', table_name='user_vocabularies')
    op.drop_table('user_vocabularies')
```

- [ ] **Step 3: Run the migration**

```bash
cd backend
alembic upgrade head
```

Expected output ends with: `Running upgrade 001 -> 002, add user_vocabularies table`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/vocabulary.py backend/alembic/versions/002_user_vocabularies.py
git commit -m "feat: add UserVocabulary model and migration"
```

---

## Task 2: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/vocabulary.py`

- [ ] **Step 1: Create the schemas**

Create `backend/app/schemas/vocabulary.py`:

```python
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VocabularyCreate(BaseModel):
    topic_id: UUID
    word: str

class VocabularyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic_id: UUID
    word: str
    added_at: datetime
    usage_count: int
    is_active: bool
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/vocabulary.py
git commit -m "feat: add vocabulary Pydantic schemas"
```

---

## Task 3: Vocabulary Service (DB + Redis)

**Files:**
- Create: `backend/app/vocabularies/__init__.py`
- Create: `backend/app/vocabularies/service.py`

- [ ] **Step 1: Create empty `__init__.py`**

Create `backend/app/vocabularies/__init__.py` with empty content.

- [ ] **Step 2: Create the service**

Create `backend/app/vocabularies/service.py`:

```python
import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vocabulary import UserVocabulary

ACTIVE_VOCAB_KEY = "active_vocab:{user_id}:{topic_id}"
VOCAB_HISTORY_KEY = "vocab_history:{user_id}:{topic_id}"
SYSTEM_PROMPT_VOCAB_KEY = "system_prompt_vocab:{user_id}:{topic_id}"

MAX_ACTIVE = 5
ACTIVE_VOCAB_TTL = 86400   # 24h
HISTORY_TTL = 3600         # 1h
SYSTEM_PROMPT_TTL = 86400  # 24h


async def list_vocabularies(db: AsyncSession, user_id: UUID, topic_id: UUID) -> list[UserVocabulary]:
    result = await db.execute(
        select(UserVocabulary)
        .where(UserVocabulary.user_id == user_id, UserVocabulary.topic_id == topic_id)
        .order_by(UserVocabulary.added_at.desc())
    )
    return result.scalars().all()


async def add_vocabulary(db: AsyncSession, redis, user_id: UUID, topic_id: UUID, word: str) -> UserVocabulary:
    vocab = UserVocabulary(user_id=user_id, topic_id=topic_id, word=word)
    db.add(vocab)
    await db.commit()
    await db.refresh(vocab)
    # Invalidate history cache so next fetch rebuilds it
    try:
        await redis.delete(VOCAB_HISTORY_KEY.format(user_id=user_id, topic_id=topic_id))
    except Exception:
        logging.warning("Redis unavailable: could not invalidate vocab_history cache")
    return vocab


async def delete_vocabulary(db: AsyncSession, redis, vocab_id: UUID, user_id: UUID) -> None:
    result = await db.execute(
        select(UserVocabulary).where(UserVocabulary.id == vocab_id, UserVocabulary.user_id == user_id)
    )
    vocab = result.scalar_one_or_none()
    if vocab is None:
        raise ValueError("Vocabulary not found")
    was_active = vocab.is_active
    topic_id = vocab.topic_id
    await db.delete(vocab)
    await db.commit()
    # Invalidate caches
    try:
        await redis.delete(VOCAB_HISTORY_KEY.format(user_id=user_id, topic_id=topic_id))
        if was_active:
            await redis.delete(ACTIVE_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id))
            await redis.delete(SYSTEM_PROMPT_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id))
    except Exception:
        logging.warning("Redis unavailable: could not invalidate caches after delete")


async def activate_vocabulary(db: AsyncSession, redis, vocab_id: UUID, user_id: UUID) -> UserVocabulary:
    result = await db.execute(
        select(UserVocabulary).where(UserVocabulary.id == vocab_id, UserVocabulary.user_id == user_id)
    )
    vocab = result.scalar_one_or_none()
    if vocab is None:
        raise ValueError("Vocabulary not found")

    # Count current active words for this user+topic
    count_result = await db.execute(
        select(func.count()).where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.topic_id == vocab.topic_id,
            UserVocabulary.is_active == True,
        )
    )
    active_count = count_result.scalar_one()
    if active_count >= MAX_ACTIVE:
        raise ValueError(f"You already have {MAX_ACTIVE} active words. Deactivate one first.")

    vocab.is_active = True
    await db.commit()
    await db.refresh(vocab)
    await _invalidate_active_caches(redis, user_id, vocab.topic_id)
    return vocab


async def deactivate_vocabulary(db: AsyncSession, redis, vocab_id: UUID, user_id: UUID) -> UserVocabulary:
    result = await db.execute(
        select(UserVocabulary).where(UserVocabulary.id == vocab_id, UserVocabulary.user_id == user_id)
    )
    vocab = result.scalar_one_or_none()
    if vocab is None:
        raise ValueError("Vocabulary not found")
    vocab.is_active = False
    await db.commit()
    await db.refresh(vocab)
    await _invalidate_active_caches(redis, user_id, vocab.topic_id)
    return vocab


async def _invalidate_active_caches(redis, user_id: UUID, topic_id: UUID) -> None:
    try:
        await redis.delete(ACTIVE_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id))
        await redis.delete(SYSTEM_PROMPT_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id))
    except Exception:
        logging.warning("Redis unavailable: could not invalidate active vocab caches")


async def get_active_vocab_words(db: AsyncSession, redis, user_id: UUID, topic_id: UUID) -> list[str]:
    """Return list of active vocab words. Redis-first, DB fallback."""
    key = ACTIVE_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id)
    try:
        cached = await redis.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        logging.warning("Redis unavailable: falling back to DB for active vocab")

    result = await db.execute(
        select(UserVocabulary.word).where(
            UserVocabulary.user_id == user_id,
            UserVocabulary.topic_id == topic_id,
            UserVocabulary.is_active == True,
        )
    )
    words = [row for row in result.scalars().all()]
    try:
        await redis.setex(key, ACTIVE_VOCAB_TTL, json.dumps(words))
    except Exception:
        pass
    return words


async def get_vocab_history_words(db: AsyncSession, redis, user_id: UUID, topic_id: UUID) -> list[str]:
    """Return latest 10 vocab words by added_at. Redis-first, DB fallback."""
    key = VOCAB_HISTORY_KEY.format(user_id=user_id, topic_id=topic_id)
    try:
        cached = await redis.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        logging.warning("Redis unavailable: falling back to DB for vocab history")

    result = await db.execute(
        select(UserVocabulary.word)
        .where(UserVocabulary.user_id == user_id, UserVocabulary.topic_id == topic_id)
        .order_by(UserVocabulary.added_at.desc())
        .limit(10)
    )
    words = [row for row in result.scalars().all()]
    try:
        await redis.setex(key, HISTORY_TTL, json.dumps(words))
    except Exception:
        pass
    return words


async def increment_usage_counts(db: AsyncSession, active_words: list[str], reply_text: str, user_id: UUID, topic_id: UUID) -> None:
    """Increment usage_count for active words that appear in reply_text (case-insensitive)."""
    reply_lower = reply_text.lower()
    matched = [w for w in active_words if w.lower() in reply_lower]
    if not matched:
        return
    try:
        from sqlalchemy import update
        await db.execute(
            update(UserVocabulary)
            .where(
                UserVocabulary.user_id == user_id,
                UserVocabulary.topic_id == topic_id,
                UserVocabulary.word.in_(matched),
            )
            .values(usage_count=UserVocabulary.usage_count + 1)
        )
        await db.commit()
    except Exception:
        logging.warning("Failed to increment vocab usage_count")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/vocabularies/__init__.py backend/app/vocabularies/service.py
git commit -m "feat: add vocabulary service with Redis caching"
```

---

## Task 4: Vocabulary Router

**Files:**
- Create: `backend/app/vocabularies/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

Create `backend/app/vocabularies/router.py`:

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.auth.dependencies import get_current_user
from app.schemas.vocabulary import VocabularyCreate, VocabularyResponse
from app.vocabularies.service import (
    list_vocabularies,
    add_vocabulary,
    delete_vocabulary,
    activate_vocabulary,
    deactivate_vocabulary,
)

router = APIRouter(prefix="/vocabularies", tags=["vocabularies"])


@router.get("", response_model=list[VocabularyResponse])
async def get_vocabularies(
    topic_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_vocabularies(db, UUID(user["sub"]), topic_id)


@router.post("", response_model=VocabularyResponse, status_code=201)
async def post_vocabulary(
    body: VocabularyCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    return await add_vocabulary(db, redis, UUID(user["sub"]), body.topic_id, body.word.strip())


@router.delete("/{vocab_id}", status_code=204)
async def del_vocabulary(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        await delete_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{vocab_id}/activate", response_model=VocabularyResponse)
async def activate_vocab(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        return await activate_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{vocab_id}/deactivate", response_model=VocabularyResponse)
async def deactivate_vocab(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        return await deactivate_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 2: Register router in `backend/app/main.py`**

Add after `from app.admin.router import router as admin_router`:

```python
from app.vocabularies.router import router as vocabularies_router
```

Add after `app.include_router(admin_router)`:

```python
app.include_router(vocabularies_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/vocabularies/router.py backend/app/main.py
git commit -m "feat: add vocabulary router and register it"
```

---

## Task 5: Enrich System Prompt in RAG Pipeline

**Files:**
- Modify: `backend/app/chat/rag.py`

- [ ] **Step 1: Replace `get_system_prompt` in `backend/app/chat/rag.py`**

The current `get_system_prompt` signature is:
```python
async def get_system_prompt(db: AsyncSession, conversation_id: UUID, redis_client) -> str:
```

Replace the entire function with this new version (keep all other functions in the file unchanged):

```python
async def get_system_prompt(
    db: AsyncSession,
    conversation_id: UUID,
    redis_client,
    user_id: UUID | None = None,
    topic_id: UUID | None = None,
) -> str:
    """Get enriched system prompt with vocab context. Cached in Redis."""
    from app.vocabularies.service import (
        get_active_vocab_words,
        get_vocab_history_words,
        SYSTEM_PROMPT_VOCAB_KEY,
        SYSTEM_PROMPT_TTL,
    )

    # Resolve topic_id if not provided
    if topic_id is None:
        result = await db.execute(
            text("SELECT topic_id FROM conversations WHERE id = :conv_id"),
            {"conv_id": str(conversation_id)},
        )
        row = result.fetchone()
        topic_id = row.topic_id if row else None

    # Check full cached system prompt (with vocab already injected)
    if user_id and topic_id:
        cache_key = SYSTEM_PROMPT_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id)
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    # Fetch base system prompt from DB (old per-conversation cache key still useful for base prompt)
    base_cache_key = f"system_prompt:{conversation_id}"
    cached_base = None
    try:
        cached_base = await redis_client.get(base_cache_key)
    except Exception:
        pass

    if cached_base:
        base_prompt = cached_base
    else:
        result = await db.execute(
            text("""
                SELECT t.system_prompt FROM topics t
                JOIN conversations c ON c.topic_id = t.id
                WHERE c.id = :conv_id
            """),
            {"conv_id": str(conversation_id)},
        )
        row = result.fetchone()
        base_prompt = row.system_prompt if row and row.system_prompt else "You are a helpful assistant."
        try:
            await redis_client.setex(base_cache_key, 3600, base_prompt)
        except Exception:
            pass

    # Build vocab-enriched prompt
    if user_id and topic_id:
        active_words = await get_active_vocab_words(db, redis_client, user_id, topic_id)
        history_words = await get_vocab_history_words(db, redis_client, user_id, topic_id)

        vocab_section = ""
        if active_words:
            vocab_section += f"\nActive vocabulary to focus on: {', '.join(active_words)}."
        if history_words:
            vocab_section += f"\nRecent vocabulary history: {', '.join(history_words)}."

        question_instruction = (
            "\n\nAlways end your response with a question to the user based on the conversation context. "
            "Exception: if the user's last message was already a question, you do not need to ask one back. "
            "If the user gave a very short or one-word answer, ask something to draw them out."
        )

        full_prompt = base_prompt + vocab_section + question_instruction

        try:
            await redis_client.setex(
                SYSTEM_PROMPT_VOCAB_KEY.format(user_id=user_id, topic_id=topic_id),
                SYSTEM_PROMPT_TTL,
                full_prompt,
            )
        except Exception:
            pass
        return full_prompt

    return base_prompt
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/chat/rag.py
git commit -m "feat: enrich system prompt with vocab context and question instruction"
```

---

## Task 6: Update Chat Service + Router

**Files:**
- Modify: `backend/app/chat/service.py`
- Modify: `backend/app/chat/router.py`
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: Update `handle_chat_message` in `backend/app/chat/service.py`**

Add `user_id` and `topic_id` parameters. After the LLM reply, load active vocab, increment usage counts, and include `active_vocab` in the return dict.

Replace the entire file content:

```python
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from openai import AsyncOpenAI
from app.config import settings
from app.models.message import Message
from app.models.conversation import Conversation
from app.chat.rag import embed_text, retrieve_context, get_recent_messages, get_system_prompt, build_messages
from app.voice.service import transcribe_audio, synthesize_speech, upload_user_audio

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def _get_topic_id(db: AsyncSession, conversation_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Conversation.topic_id).where(Conversation.id == conversation_id)
    )
    row = result.scalar_one_or_none()
    return row


async def handle_chat_message(
    db: AsyncSession,
    redis_client,
    conversation_id: UUID,
    text_content: str | None,
    audio_bytes: bytes | None,
    audio_filename: str,
    reply_with_voice: bool,
    user_id: UUID | None = None,
) -> dict:
    """
    Full RAG chat pipeline. Returns dict with user/assistant message IDs, content, audio URLs, and active_vocab.
    """
    user_audio_url = None

    # 1. Transcribe and upload user audio if provided
    if audio_bytes:
        text_content = await transcribe_audio(audio_bytes, audio_filename)
        try:
            user_audio_url = await upload_user_audio(audio_bytes, audio_filename)
        except Exception:
            logging.warning("Failed to upload user audio to S3 — storing message without audio_url")

    if not text_content:
        raise ValueError("No text content to process")

    # 2. Resolve topic_id for vocab lookups
    topic_id = await _get_topic_id(db, conversation_id) if user_id else None

    # 3. Embed user message
    embedding = await embed_text(text_content)

    # 4. Store user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=text_content,
        audio_url=user_audio_url,
        embedding=embedding,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # 5. Retrieve context + enriched system prompt
    semantic_ctx = await retrieve_context(db, conversation_id, embedding)
    recent = await get_recent_messages(db, conversation_id)
    system_prompt = await get_system_prompt(
        db, conversation_id, redis_client,
        user_id=user_id,
        topic_id=topic_id,
    )

    # 6. Build prompt and call LLM
    messages = await build_messages(system_prompt, semantic_ctx, recent, text_content)
    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    reply_text = completion.choices[0].message.content

    # 7. Embed and store assistant message
    reply_embedding = await embed_text(reply_text)
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_text,
        embedding=reply_embedding,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    # 8. Load active vocab and increment usage counts (fire-and-forget)
    active_vocab: list[str] = []
    if user_id and topic_id:
        try:
            from app.vocabularies.service import get_active_vocab_words, increment_usage_counts
            active_vocab = await get_active_vocab_words(db, redis_client, user_id, topic_id)
            await increment_usage_counts(db, active_vocab, reply_text, user_id, topic_id)
        except Exception:
            logging.warning("Failed to load/increment vocab usage counts")

    # 9. TTS if requested
    audio_url = None
    if reply_with_voice:
        try:
            audio_url = await synthesize_speech(reply_text)
        except Exception:
            audio_url = None

    return {
        "user_message_id": user_msg.id,
        "user_audio_url": user_audio_url,
        "transcribed_text": text_content,
        "content": reply_text,
        "assistant_message_id": assistant_msg.id,
        "audio_url": audio_url,
        "active_vocab": active_vocab,
        "created_at_user": user_msg.created_at,
        "created_at_assistant": assistant_msg.created_at,
    }
```

- [ ] **Step 2: Update `backend/app/schemas/chat.py` — add `active_vocab` to `ChatSendResponse`**

Replace `ChatSendResponse`:

```python
class ChatSendResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    active_vocab: list[str] = []
```

- [ ] **Step 3: Update `backend/app/chat/router.py` — pass `user_id` and include `active_vocab` in response**

In the `send_message` handler, update the `handle_chat_message` call to pass `user_id`:

```python
result = await handle_chat_message(
    db, redis_client, conversation_id,
    text_content=content,
    audio_bytes=audio_bytes,
    audio_filename=audio_filename,
    reply_with_voice=reply_with_voice,
    user_id=UUID(user["sub"]),
)
```

Update the return statement:

```python
return ChatSendResponse(
    user_message=MessageOut(
        id=result["user_message_id"],
        role="user",
        content=content or result.get("transcribed_text", ""),
        audio_url=result["user_audio_url"],
        created_at=result["created_at_user"],
    ),
    assistant_message=MessageOut(
        id=result["assistant_message_id"],
        role="assistant",
        content=result["content"],
        audio_url=result["audio_url"],
        created_at=result["created_at_assistant"],
    ),
    active_vocab=result.get("active_vocab", []),
)
```

Also add `from uuid import UUID` to imports if not already present (it is — check line 2).

- [ ] **Step 4: Commit**

```bash
git add backend/app/chat/service.py backend/app/chat/router.py backend/app/schemas/chat.py
git commit -m "feat: pass user_id through chat pipeline, return active_vocab in response"
```

---

## Task 7: Frontend — API Types + Vocab API

**Files:**
- Modify: `frontend/src/api/endpoints.ts`

- [ ] **Step 1: Update `frontend/src/api/endpoints.ts`**

Add after the existing `ChatSendResponse` interface (update the existing one and add vocab types):

```typescript
// Update existing ChatSendResponse to add active_vocab
export interface ChatSendResponse {
  user_message: MessageOut
  assistant_message: MessageOut
  active_vocab: string[]
}

export interface VocabularyItem {
  id: string
  user_id: string
  topic_id: string
  word: string
  added_at: string
  usage_count: number
  is_active: boolean
}

export const vocabularyApi = {
  list: (topic_id: string) =>
    client.get<VocabularyItem[]>("/vocabularies", { params: { topic_id } }),
  add: (topic_id: string, word: string) =>
    client.post<VocabularyItem>("/vocabularies", { topic_id, word }),
  delete: (id: string) => client.delete(`/vocabularies/${id}`),
  activate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/activate`),
  deactivate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/deactivate`),
}
```

Note: The existing `ChatSendResponse` in the file does not have `active_vocab` — replace the existing interface definition (lines 41-44 in `endpoints.ts`) with the updated one above.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/endpoints.ts
git commit -m "feat: add vocabulary API types and client methods"
```

---

## Task 8: Frontend — VocabularyPage

**Files:**
- Create: `frontend/src/pages/VocabularyPage.tsx`

- [ ] **Step 1: Create the vocabulary management page**

Create `frontend/src/pages/VocabularyPage.tsx`:

```tsx
import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { vocabularyApi } from "../api/endpoints"
import type { VocabularyItem } from "../api/endpoints"

export default function VocabularyPage() {
  const { topicId } = useParams<{ topicId: string }>()
  const navigate = useNavigate()
  const [words, setWords] = useState<VocabularyItem[]>([])
  const [newWord, setNewWord] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (topicId) {
      vocabularyApi.list(topicId).then(r => setWords(r.data))
    }
  }, [topicId])

  const handleAdd = async () => {
    const trimmed = newWord.trim()
    if (!trimmed || !topicId) return
    setError(null)
    try {
      const res = await vocabularyApi.add(topicId, trimmed)
      setWords(prev => [res.data, ...prev])
      setNewWord("")
    } catch {
      setError("Failed to add word.")
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await vocabularyApi.delete(id)
      setWords(prev => prev.filter(w => w.id !== id))
    } catch {
      setError("Failed to delete word.")
    }
  }

  const handleToggleActive = async (item: VocabularyItem) => {
    setError(null)
    try {
      const res = item.is_active
        ? await vocabularyApi.deactivate(item.id)
        : await vocabularyApi.activate(item.id)
      setWords(prev => prev.map(w => w.id === item.id ? res.data : w))
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Failed to update word."
      setError(msg)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back to Topics
        </button>
        <h1 className="text-2xl font-bold">My Vocabulary</h1>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={newWord}
          onChange={e => setNewWord(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleAdd()}
          placeholder="Add a new word..."
          className="flex-1 border rounded px-3 py-2 text-sm"
        />
        <button
          onClick={handleAdd}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
        >
          Add
        </button>
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <table className="w-full bg-white border rounded-lg text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="px-4 py-2">Word</th>
            <th className="px-4 py-2">Added</th>
            <th className="px-4 py-2">Times Used</th>
            <th className="px-4 py-2">Active</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {words.map(item => (
            <tr key={item.id} className="border-b last:border-0">
              <td className="px-4 py-2 font-medium">{item.word}</td>
              <td className="px-4 py-2 text-gray-500">{new Date(item.added_at).toLocaleDateString()}</td>
              <td className="px-4 py-2 text-gray-500">{item.usage_count}</td>
              <td className="px-4 py-2">
                <button
                  onClick={() => handleToggleActive(item)}
                  className={`px-2 py-1 rounded text-xs ${item.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                >
                  {item.is_active ? "Active" : "Inactive"}
                </button>
              </td>
              <td className="px-4 py-2">
                <button
                  onClick={() => handleDelete(item.id)}
                  className="text-red-400 hover:text-red-600 text-xs"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {words.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-gray-400">No words yet. Add your first word above.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/VocabularyPage.tsx
git commit -m "feat: add VocabularyPage UI"
```

---

## Task 9: Frontend — Wire Up Route + TopicsPage Link

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/TopicsPage.tsx`

- [ ] **Step 1: Add route to `frontend/src/App.tsx`**

Add import after `import ChatPage`:
```tsx
import VocabularyPage from "./pages/VocabularyPage"
```

Add route inside `<Routes>` after the `/chat/:conversationId` route:
```tsx
<Route path="/topics/:topicId/vocabulary" element={<PrivateRoute><VocabularyPage /></PrivateRoute>} />
```

- [ ] **Step 2: Add "Vocabulary" button in `frontend/src/pages/TopicsPage.tsx`**

Replace the topic card button block (currently lines 39-43) with a card + vocabulary link:

```tsx
{topics.map(t => (
  <div key={t.id} className="bg-white border rounded-lg p-4 space-y-2 hover:shadow-md transition">
    <button onClick={() => startChat(t.id)} className="w-full text-left">
      <h2 className="font-semibold">{t.name}</h2>
      {t.description && <p className="text-gray-500 text-sm mt-1">{t.description}</p>}
    </button>
    <button
      onClick={() => navigate(`/topics/${t.id}/vocabulary`)}
      className="text-xs text-blue-500 hover:underline"
    >
      Vocabulary →
    </button>
  </div>
))}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/TopicsPage.tsx
git commit -m "feat: add vocabulary route and link from topics page"
```

---

## Task 10: Frontend — Vocab Highlighting in Chat

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`
- Modify: `frontend/src/components/MessageBubble.tsx`
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: Update `useChat` to expose `activeVocab`**

In `frontend/src/hooks/useChat.ts`, add `activeVocab` state and update it from chat responses.

Replace the full file:

```typescript
import { useState, useCallback, useEffect } from "react"
import { chatApi } from "../api/endpoints"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeVocab, setActiveVocab] = useState<string[]>([])

  // Load history on mount
  useEffect(() => {
    let cancelled = false
    async function loadHistory() {
      try {
        const res = await chatApi.history(conversationId)
        if (!cancelled) {
          setMessages(res.data.messages.map(m => ({
            role: m.role,
            content: m.content,
            audio_url: m.audio_url,
          })))
        }
      } catch {
        // Silently ignore — empty chat is fine
      }
    }
    loadHistory()
    return () => { cancelled = true }
  }, [conversationId])

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.sendText(conversationId, content, replyWithVoice)
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  const sendVoice = useCallback(async (audioBlob: Blob, replyWithVoice: boolean) => {
    setError(null)
    setLoading(true)
    try {
      const res = await chatApi.sendAudio(conversationId, audioBlob, replyWithVoice)
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
      setMessages(prev => [
        ...prev,
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  return { messages, loading, error, sendText, sendVoice, activeVocab }
}
```

- [ ] **Step 2: Update `MessageBubble` to highlight vocab words**

Replace `frontend/src/components/MessageBubble.tsx`:

```tsx
import type { ChatMessage } from "../hooks/useChat"

function highlightVocab(content: string, activeVocab: string[]): React.ReactNode {
  if (!activeVocab.length) return content

  const pattern = new RegExp(`(${activeVocab.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})`, "gi")
  const parts = content.split(pattern)

  return parts.map((part, i) => {
    const isMatch = activeVocab.some(w => w.toLowerCase() === part.toLowerCase())
    return isMatch
      ? <mark key={i} className="bg-yellow-200 rounded px-0.5">{part}</mark>
      : part
  })
}

export default function MessageBubble({
  message,
  activeVocab = [],
}: {
  message: ChatMessage
  activeVocab?: string[]
}) {
  const isUser = message.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800"}`}>
        <p className="text-sm">
          {isUser ? message.content : highlightVocab(message.content, activeVocab)}
        </p>
        {message.audio_url && (
          <audio controls src={message.audio_url} className="mt-2 w-full" />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update `ChatPage` to pass `activeVocab` to `MessageBubble`**

In `frontend/src/pages/ChatPage.tsx`, update the `useChat` destructuring and `MessageBubble` usage:

```tsx
const { messages, loading, error, sendText, sendVoice, activeVocab } = useChat(conversationId!)
```

Update the messages render line:
```tsx
{messages.map((m, i) => <MessageBubble key={i} message={m} activeVocab={m.role === "assistant" ? activeVocab : []} />)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useChat.ts frontend/src/components/MessageBubble.tsx frontend/src/pages/ChatPage.tsx
git commit -m "feat: highlight active vocab words in assistant messages"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `user_vocabularies` table — Task 1
- [x] CRUD + activate/deactivate endpoints — Tasks 3, 4
- [x] Redis caching for `active_vocab`, `vocab_history`, `system_prompt_vocab` — Task 3 (service)
- [x] Cache invalidation on activate/deactivate/delete — Task 3 (service)
- [x] Enriched system prompt with vocab + question instruction — Task 5
- [x] `usage_count` increment after LLM reply — Task 6
- [x] `active_vocab` in chat response payload — Task 6
- [x] VocabularyPage UI — Task 8
- [x] Vocabulary link from TopicsPage — Task 9
- [x] Route registration — Task 9
- [x] Vocab highlighting in MessageBubble — Task 10
- [x] Max 5 active words enforced — Task 3 (`activate_vocabulary`)
- [x] DB fallback for all Redis reads — Task 3 (service)
- [x] Alembic migration — Task 1

**Type consistency:**
- `get_active_vocab_words` defined in Task 3, used in Tasks 5 and 6 ✓
- `get_vocab_history_words` defined in Task 3, used in Task 5 ✓
- `increment_usage_counts` defined in Task 3, used in Task 6 ✓
- `SYSTEM_PROMPT_VOCAB_KEY`, `SYSTEM_PROMPT_TTL` defined in Task 3, imported in Task 5 ✓
- `active_vocab: list[str]` in service return → `active_vocab: list[str] = []` in schema → `active_vocab: string[]` in TS ✓
- `VocabularyItem` interface defined in Task 7, used in Tasks 8 ✓
- `activeVocab` prop added to `MessageBubble` in Task 10, passed from `ChatPage` in Task 10 ✓
