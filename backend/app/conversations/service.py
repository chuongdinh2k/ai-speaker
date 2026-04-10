from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID
from app.models.conversation import Conversation

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

async def list_conversations(db: AsyncSession, user_id: UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    return result.scalars().all()

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
    conversation.deleted_at = datetime.utcnow()
    await db.commit()
