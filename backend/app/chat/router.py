import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.redis_client import get_redis
from app.auth.dependencies import get_current_user
from app.chat.service import handle_chat_message
from app.models.message import Message
from app.schemas.chat import ChatSendResponse, ChatHistoryResponse, MessageOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    conversation_id: UUID = Form(...),
    content: Optional[str] = Form(None),
    reply_with_voice: bool = Form(False),
    audio: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if content is None and audio is None:
        raise HTTPException(status_code=422, detail="Provide either content or audio.")
    if content is not None and audio is not None:
        raise HTTPException(status_code=422, detail="Provide content or audio, not both.")

    audio_bytes = None
    audio_filename = "audio.webm"
    if audio is not None:
        audio_bytes = await audio.read()
        audio_filename = audio.filename or "audio.webm"

    redis_client = await get_redis()
    try:
        result = await handle_chat_message(
            db, redis_client, conversation_id,
            text_content=content,
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            reply_with_voice=reply_with_voice,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logging.exception("Chat error")
        raise HTTPException(status_code=500, detail="An error occurred. Please try again.")

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
    )


@router.get("/{conversation_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_history(
    conversation_id: UUID,
    cursor: Optional[UUID] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Message).where(Message.conversation_id == conversation_id)

    if cursor is not None:
        cursor_result = await db.execute(
            select(Message.created_at).where(Message.id == cursor)
        )
        cursor_row = cursor_result.scalar_one_or_none()
        if cursor_row is None:
            raise HTTPException(status_code=404, detail="Cursor message not found.")
        query = query.where(Message.created_at < cursor_row)

    query = query.order_by(Message.created_at.desc(), Message.id.desc()).limit(10)
    result = await db.execute(query)
    messages = result.scalars().all()

    # Re-sort ascending so the UI renders oldest→newest
    messages = sorted(messages, key=lambda m: m.created_at)

    next_cursor = messages[0].id if len(messages) == 10 else None

    return ChatHistoryResponse(
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                audio_url=m.audio_url,
                created_at=m.created_at,
            )
            for m in messages
        ],
        next_cursor=next_cursor,
    )
