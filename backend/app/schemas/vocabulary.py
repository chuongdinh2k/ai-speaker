from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class VocabularyCreate(BaseModel):
    topic_id: UUID
    word: str

class VocabularyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic_id: UUID
    word: str
    added_at: datetime
    usage_count: int
    is_active: bool


class VocabularyWithTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic_id: UUID
    topic_name: str
    word: str
    added_at: datetime
    usage_count: int
    is_active: bool
