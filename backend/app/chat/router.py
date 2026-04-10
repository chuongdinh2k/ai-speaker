import base64
import json
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from app.config import settings
from app.database import get_db
from app.redis_client import get_redis
from app.chat.service import handle_chat_message

router = APIRouter(tags=["chat"])

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    # Authenticate
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    redis_client = await get_redis()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "code": "INVALID_JSON", "message": "Invalid JSON"}))
                continue

            msg_type = data.get("type")
            reply_with_voice = data.get("reply_with_voice", False)

            try:
                if msg_type == "text":
                    result = await handle_chat_message(
                        db, redis_client, conversation_id,
                        text_content=data.get("content"),
                        audio_bytes=None,
                        reply_with_voice=reply_with_voice,
                    )
                elif msg_type == "voice":
                    audio_bytes = base64.b64decode(data.get("audio_base64", ""))
                    result = await handle_chat_message(
                        db, redis_client, conversation_id,
                        text_content=None,
                        audio_bytes=audio_bytes,
                        reply_with_voice=reply_with_voice,
                    )
                else:
                    await websocket.send_text(json.dumps({"type": "error", "code": "UNKNOWN_TYPE", "message": "Unknown message type"}))
                    continue

                await websocket.send_text(json.dumps({"type": "message", "content": result["content"], "audio_url": result["audio_url"]}))

            except Exception as e:
                import logging
                logging.exception("Chat error")
                await websocket.send_text(json.dumps({"type": "error", "code": "CHAT_ERROR", "message": "An error occurred. Please try again."}))

    except WebSocketDisconnect:
        pass
