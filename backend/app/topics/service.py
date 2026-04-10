from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.topic import Topic

async def list_topics(db: AsyncSession) -> list[Topic]:
    result = await db.execute(select(Topic))
    return result.scalars().all()

async def create_topic(db: AsyncSession, name: str, description: str | None, system_prompt: str | None) -> Topic:
    topic = Topic(name=name, description=description, system_prompt=system_prompt)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

async def update_topic(db: AsyncSession, topic_id: str, name: str | None, description: str | None, system_prompt: str | None) -> Topic:
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise ValueError("Topic not found")
    if name is not None:
        topic.name = name
    if description is not None:
        topic.description = description
    if system_prompt is not None:
        topic.system_prompt = system_prompt
    await db.commit()
    await db.refresh(topic)
    return topic
