from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class ConversationCreate(BaseModel):
    topic_id: UUID


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    created_at: datetime
    message_count: int = 0
