import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from uuid import UUID
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.topic import Topic


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
        select(Conversation, Topic.name.label("topic_name"), msg_count.label("message_count"))
        .join(Topic, Conversation.topic_id == Topic.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    rows = result.all()
    out = []
    for conv, topic_name, count in rows:
        out.append({
            "id": conv.id,
            "topic_id": conv.topic_id,
            "topic_name": topic_name,
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


async def update_conversation_context(
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    name: str,
    occupation: str,
    learning_goal: str,
    preferred_tone: str,
) -> Conversation:
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

    topic_result = await db.execute(
        select(Topic).where(Topic.id == conversation.topic_id)
    )
    topic = topic_result.scalar_one_or_none()
    base_prompt = topic.system_prompt if topic and topic.system_prompt else "You are a helpful assistant."

    combined_prompt = (
        f"{base_prompt}\n\n"
        f"User context:\n"
        f"- Name: {name}\n"
        f"- Occupation: {occupation}\n"
        f"- Learning goal: {learning_goal}\n"
        f"- Preferred tone: {preferred_tone}"
    )

    conversation.user_context = {
        "name": name,
        "occupation": occupation,
        "learning_goal": learning_goal,
        "preferred_tone": preferred_tone,
    }
    conversation.conversation_prompt = combined_prompt
    await db.commit()
    await db.refresh(conversation)
    return conversation
