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

async def get_system_prompt(db: AsyncSession, conversation_id: UUID, redis_client) -> str:
    """Get topic system prompt, cached in Redis."""
    cache_key = f"system_prompt:{conversation_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        text("""
            SELECT t.system_prompt FROM topics t
            JOIN conversations c ON c.topic_id = t.id
            WHERE c.id = :conv_id
        """),
        {"conv_id": str(conversation_id)},
    )
    row = result.fetchone()
    prompt = row.system_prompt if row and row.system_prompt else "You are a helpful assistant."
    await redis_client.setex(cache_key, 3600, prompt)
    return prompt

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
