from uuid import UUID
from pydantic import BaseModel

class ChatSendRequest(BaseModel):
    conversation_id: UUID
    content: str
    reply_with_voice: bool = False

class MessageOut(BaseModel):
    id: UUID
    content: str
    audio_url: str | None = None

class ChatSendResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
