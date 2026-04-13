from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ChatSendRequest(BaseModel):
    conversation_id: UUID
    content: str
    reply_with_voice: bool = False


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    audio_url: str | None = None
    created_at: datetime


class ChatSendResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


class ChatHistoryResponse(BaseModel):
    messages: list[MessageOut]
    next_cursor: UUID | None = None
