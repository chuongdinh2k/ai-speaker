import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from openai import AsyncOpenAI
from app.models.message import Message
from app.models.topic import Topic
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_text(text_content: str) -> list[float]:
    """Embed a string using OpenAI embeddings, return vector."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text_content,
    )
    return response.data[0].embedding

async def retrieve_context(db: AsyncSession, conversation_id: UUID, query_embedding: list[float]) -> list[dict]:
    """Retrieve top-K semantically similar messages from this conversation."""
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    result = await db.execute(
        text("""
            SELECT role, content FROM messages
            WHERE conversation_id = :conv_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :k
        """),
        {"conv_id": str(conversation_id), "embedding": embedding_str, "k": settings.rag_top_k},
    )
    return [{"role": row.role, "content": row.content} for row in result]

async def get_recent_messages(db: AsyncSession, conversation_id: UUID) -> list[dict]:
    """Get last N messages for recency anchor."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.rag_recent_window)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]

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

async def build_messages(system_prompt: str, semantic_context: list[dict], recent: list[dict], user_text: str) -> list[dict]:
    """Assemble the messages list for the LLM call."""
    seen = set()
    combined = []
    for msg in semantic_context + recent:
        key = (msg["role"], msg["content"])
        if key not in seen:
            seen.add(key)
            combined.append(msg)
    return [{"role": "system", "content": system_prompt}] + combined + [{"role": "user", "content": user_text}]
