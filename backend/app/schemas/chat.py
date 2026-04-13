from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    audio_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSendResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut


class ChatHistoryResponse(BaseModel):
    messages: list[MessageOut]
    next_cursor: UUID | None = None
