import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from uuid import UUID
from app.models.conversation import Conversation
from app.models.message import Message


async def upsert_conversation(db: AsyncSession, user_id: UUID, topic_id: UUID) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.topic_id == topic_id,
            Conversation.deleted_at == None,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation
    conversation = Conversation(user_id=user_id, topic_id=topic_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, user_id: UUID) -> list[dict]:
    msg_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Conversation, msg_count.label("message_count")).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    rows = result.all()
    out = []
    for conv, count in rows:
        out.append({
            "id": conv.id,
            "topic_id": conv.topic_id,
            "created_at": conv.created_at,
            "message_count": count,
        })
    return out


async def delete_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")
    conversation.deleted_at = datetime.now(timezone.utc)
    await db.commit()
