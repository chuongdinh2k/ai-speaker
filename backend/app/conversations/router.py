import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationContextUpdate, ConversationContextResponse
from app.conversations.service import upsert_conversation, list_conversations, delete_conversation, update_conversation_context
from app.auth.dependencies import get_current_user
from app.redis_client import get_redis

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "none"]

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    rows = await list_conversations(db, UUID(user["sub"]))
    return [ConversationResponse(**row) for row in rows]


@router.post("", response_model=ConversationResponse, status_code=201)
async def post_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    conv = await upsert_conversation(db, UUID(user["sub"]), body.topic_id)
    return ConversationResponse(
        id=conv.id,
        topic_id=conv.topic_id,
        created_at=conv.created_at,
        message_count=0,
    )


@router.delete("/{conversation_id}", status_code=204)
async def del_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        await delete_conversation(db, conversation_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{conversation_id}/context", response_model=ConversationContextResponse)
async def patch_conversation_context(
    conversation_id: UUID,
    body: ConversationContextUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        conv = await update_conversation_context(
            db,
            conversation_id,
            UUID(user["sub"]),
            name=body.name,
            occupation=body.occupation,
            learning_goal=body.learning_goal,
            preferred_tone=body.preferred_tone,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    redis_client = await get_redis()
    try:
        await redis_client.delete(f"system_prompt:{conversation_id}")
        for level in LEVELS:
            await redis_client.delete(f"system_prompt_vocab:{user['sub']}:{conv.topic_id}:{level}")
    except Exception:
        logging.warning("Failed to invalidate Redis cache after context update")

    return ConversationContextResponse(
        id=conv.id,
        topic_id=conv.topic_id,
        user_context=conv.user_context,
        conversation_prompt=conv.conversation_prompt,
    )
