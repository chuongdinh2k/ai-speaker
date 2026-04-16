import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.vocabulary import UserVocabulary

ACTIVE_VOCAB_KEY = "active_vocab:{user_id}:{topic_id}"
VOCAB_HISTORY_KEY = "vocab_history:{user_id}:{topic_id}"

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
            for _level in ["A1", "A2", "B1", "B2", "C1", "C2", "none"]:
                await redis.delete(f"system_prompt_vocab:{user_id}:{topic_id}:{_level}")
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
        for _level in ["A1", "A2", "B1", "B2", "C1", "C2", "none"]:
            await redis.delete(f"system_prompt_vocab:{user_id}:{topic_id}:{_level}")
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
