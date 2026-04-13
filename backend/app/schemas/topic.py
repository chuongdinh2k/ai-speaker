from pydantic import BaseModel, ConfigDict
from uuid import UUID

class TopicCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None

class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None

class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    system_prompt: str | None
