import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from openai import AsyncOpenAI
from app.config import settings
from app.models.message import Message
from app.models.conversation import Conversation
from app.chat.rag import embed_text, retrieve_context, get_recent_messages, get_system_prompt, build_messages
from app.voice.service import transcribe_audio, synthesize_speech, upload_user_audio

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def _get_topic_id(db: AsyncSession, conversation_id: UUID) -> UUID | None:
    result = await db.execute(
        select(Conversation.topic_id).where(Conversation.id == conversation_id)
    )
    row = result.scalar_one_or_none()
    return row


async def handle_chat_message(
    db: AsyncSession,
    redis_client,
    conversation_id: UUID,
    text_content: str | None,
    audio_bytes: bytes | None,
    audio_filename: str,
    reply_with_voice: bool,
    user_id: UUID | None = None,
) -> dict:
    """
    Full RAG chat pipeline. Returns dict with user/assistant message IDs, content, audio URLs, and active_vocab.
    """
    user_audio_url = None

    # 1. Transcribe and upload user audio if provided
    if audio_bytes:
        text_content = await transcribe_audio(audio_bytes, audio_filename)
        try:
            user_audio_url = await upload_user_audio(audio_bytes, audio_filename)
        except Exception:
            logging.warning("Failed to upload user audio to S3 — storing message without audio_url")

    if not text_content:
        raise ValueError("No text content to process")

    # 2. Resolve topic_id for vocab lookups
    topic_id = await _get_topic_id(db, conversation_id) if user_id else None

    # 3. Embed user message
    embedding = await embed_text(text_content)

    # 4. Store user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=text_content,
        audio_url=user_audio_url,
        embedding=embedding,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # 5. Retrieve context + enriched system prompt
    semantic_ctx = await retrieve_context(db, conversation_id, embedding)
    recent = await get_recent_messages(db, conversation_id)
    system_prompt = await get_system_prompt(
        db, conversation_id, redis_client,
        user_id=user_id,
        topic_id=topic_id,
    )

    # 6. Build prompt and call LLM
    messages = await build_messages(system_prompt, semantic_ctx, recent, text_content)
    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    reply_text = completion.choices[0].message.content

    # 7. Embed and store assistant message
    reply_embedding = await embed_text(reply_text)
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_text,
        embedding=reply_embedding,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    # 8. Load active vocab and increment usage counts (fire-and-forget)
    active_vocab: list[str] = []
    if user_id and topic_id:
        try:
            from app.vocabularies.service import get_active_vocab_words, increment_usage_counts
            active_vocab = await get_active_vocab_words(db, redis_client, user_id, topic_id)
            await increment_usage_counts(db, active_vocab, reply_text, user_id, topic_id)
        except Exception:
            logging.warning("Failed to load/increment vocab usage counts")

    # 9. TTS if requested
    audio_url = None
    if reply_with_voice:
        try:
            audio_url = await synthesize_speech(reply_text)
        except Exception:
            audio_url = None

    return {
        "user_message_id": user_msg.id,
        "user_audio_url": user_audio_url,
        "transcribed_text": text_content,
        "content": reply_text,
        "assistant_message_id": assistant_msg.id,
        "audio_url": audio_url,
        "active_vocab": active_vocab,
        "created_at_user": user_msg.created_at,
        "created_at_assistant": assistant_msg.created_at,
    }
