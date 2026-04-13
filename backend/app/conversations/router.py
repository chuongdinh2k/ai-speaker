from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.conversations.service import upsert_conversation, list_conversations, delete_conversation
from app.auth.dependencies import get_current_user

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
