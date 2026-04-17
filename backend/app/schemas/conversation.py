from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Literal


class ConversationCreate(BaseModel):
    topic_id: UUID


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    topic_name: str = ""
    created_at: datetime
    message_count: int = 0


class ConversationContextUpdate(BaseModel):
    name: str
    occupation: str
    learning_goal: str
    preferred_tone: Literal["formal", "casual", "friendly"]


class ConversationContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    user_context: dict | None
    conversation_prompt: str | None
