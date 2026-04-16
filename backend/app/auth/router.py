from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.auth.service import register_user, authenticate_user, create_access_token
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.message import Message
from app.models.conversation import Conversation

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(id=str(user.id), email=user.email, role=user.role)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    token = create_access_token(user)
    return TokenResponse(access_token=token)

@router.post("/logout")
async def logout():
    return {"message": "logged out"}

@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.id == UUID(user["sub"]), User.deleted_at.is_(None))
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    count_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == db_user.id,
            Message.role == "user",
        )
    )
    total_messages = count_result.scalar_one() or 0

    return UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        role=db_user.role,
        level=db_user.level,
        avatar_url=db_user.avatar_url,
        total_messages=total_messages,
    )
