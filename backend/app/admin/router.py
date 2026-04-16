from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from passlib.context import CryptContext
from app.database import get_db
from app.models.topic import Topic
from app.models.user import User
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ── Schemas ──────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: str
    email: str
    role: str
    level: str
    created_at: datetime

class UpdatePasswordRequest(BaseModel):
    password: str

class AdminTopicOut(BaseModel):
    id: str
    name: str
    description: str | None
    system_prompt: str | None
    created_at: datetime

class CreateTopicRequest(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None

class UpdateTopicRequest(BaseModel):
    description: str | None = None
    system_prompt: str | None = None


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.deleted_at.is_(None)))
    users = result.scalars().all()
    return [
        AdminUserOut(id=str(u.id), email=u.email, role=u.role, level=u.level, created_at=u.created_at)
        for u in users
    ]

@router.patch("/users/{user_id}/password")
async def update_user_password(
    user_id: str,
    body: UpdatePasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = pwd_context.hash(body.password)
    await db.commit()
    return {"ok": True}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


# ── Topics ────────────────────────────────────────────────────────────────────

@router.get("/topics", response_model=list[AdminTopicOut])
async def list_topics(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Topic).where(Topic.deleted_at.is_(None)))
    topics = result.scalars().all()
    return [
        AdminTopicOut(
            id=str(t.id), name=t.name, description=t.description,
            system_prompt=t.system_prompt, created_at=t.created_at
        )
        for t in topics
    ]

@router.post("/topics", response_model=AdminTopicOut, status_code=201)
async def create_topic(
    body: CreateTopicRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    topic = Topic(name=body.name, description=body.description, system_prompt=body.system_prompt)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return AdminTopicOut(
        id=str(topic.id), name=topic.name, description=topic.description,
        system_prompt=topic.system_prompt, created_at=topic.created_at
    )

@router.patch("/topics/{topic_id}", response_model=AdminTopicOut)
async def update_topic(
    topic_id: str,
    body: UpdateTopicRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Topic).where(Topic.id == UUID(topic_id), Topic.deleted_at.is_(None)))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if body.description is not None:
        topic.description = body.description
    if body.system_prompt is not None:
        topic.system_prompt = body.system_prompt
    await db.commit()
    await db.refresh(topic)
    return AdminTopicOut(
        id=str(topic.id), name=topic.name, description=topic.description,
        system_prompt=topic.system_prompt, created_at=topic.created_at
    )

@router.delete("/topics/{topic_id}")
async def delete_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Topic).where(Topic.id == UUID(topic_id), Topic.deleted_at.is_(None)))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}
