from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ConversationCreate(BaseModel):
    topic_id: UUID


class ConversationResponse(BaseModel):
    id: UUID
    topic_id: UUID
    created_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True
