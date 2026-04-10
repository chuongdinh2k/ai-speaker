from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.topics.service import list_topics, create_topic, update_topic
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("", response_model=list[TopicResponse])
async def get_topics(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    return await list_topics(db)

@router.post("", response_model=TopicResponse, status_code=201)
async def post_topic(body: TopicCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    return await create_topic(db, body.name, body.description, body.system_prompt)

@router.put("/{topic_id}", response_model=TopicResponse)
async def put_topic(topic_id: str, body: TopicUpdate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    try:
        return await update_topic(db, topic_id, body.name, body.description, body.system_prompt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
