from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.topic import Topic
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

class UpdatePromptRequest(BaseModel):
    system_prompt: str

@router.put("/topics/{topic_id}/prompt")
async def update_topic_prompt(
    topic_id: str,
    body: UpdatePromptRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic.system_prompt = body.system_prompt
    await db.commit()
    return {"id": str(topic.id), "system_prompt": topic.system_prompt}
