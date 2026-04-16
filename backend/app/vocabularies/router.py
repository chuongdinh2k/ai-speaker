from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.auth.dependencies import get_current_user
from app.schemas.vocabulary import VocabularyCreate, VocabularyResponse, VocabularyWithTopicResponse
from app.vocabularies.service import (
    list_vocabularies,
    add_vocabulary,
    delete_vocabulary,
    activate_vocabulary,
    deactivate_vocabulary,
    list_all_vocabularies,
)

router = APIRouter(prefix="/vocabularies", tags=["vocabularies"])


@router.get("/all", response_model=list[VocabularyWithTopicResponse])
async def get_all_vocabularies(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_all_vocabularies(db, UUID(user["sub"]))
    return rows


@router.get("", response_model=list[VocabularyResponse])
async def get_vocabularies(
    topic_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_vocabularies(db, UUID(user["sub"]), topic_id)


@router.post("", response_model=VocabularyResponse, status_code=201)
async def post_vocabulary(
    body: VocabularyCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    return await add_vocabulary(db, redis, UUID(user["sub"]), body.topic_id, body.word.strip())


@router.delete("/{vocab_id}", status_code=204)
async def del_vocabulary(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        await delete_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{vocab_id}/activate", response_model=VocabularyResponse)
async def activate_vocab(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        return await activate_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{vocab_id}/deactivate", response_model=VocabularyResponse)
async def deactivate_vocab(
    vocab_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    try:
        return await deactivate_vocabulary(db, redis, vocab_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
