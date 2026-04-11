import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.auth.dependencies import get_current_user
from app.chat.service import handle_chat_message
from app.schemas.chat import ChatSendRequest, ChatSendResponse, MessageOut

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    body: ChatSendRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    try:
        result = await handle_chat_message(
            db, redis_client, body.conversation_id,
            text_content=body.content,
            audio_bytes=None,
            reply_with_voice=body.reply_with_voice,
        )
    except Exception:
        logging.exception("Chat error")
        raise HTTPException(status_code=500, detail="An error occurred. Please try again.")

    return ChatSendResponse(
        user_message=MessageOut(id=result["user_message_id"], content=body.content),
        assistant_message=MessageOut(
            id=result["assistant_message_id"],
            content=result["content"],
            audio_url=result["audio_url"],
        ),
    )
