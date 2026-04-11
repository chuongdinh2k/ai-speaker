from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.models.message import Message
from app.chat.rag import embed_text, retrieve_context, get_recent_messages, get_system_prompt, build_messages
from app.voice.service import transcribe_audio, synthesize_speech

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

async def handle_chat_message(
    db: AsyncSession,
    redis_client,
    conversation_id: UUID,
    text_content: str | None,
    audio_bytes: bytes | None,
    reply_with_voice: bool,
) -> dict:
    """
    Full RAG chat pipeline. Returns {"content": str, "audio_url": str | None}.
    Raises Exception on unrecoverable errors.
    """
    # 1. Resolve text
    if audio_bytes:
        text_content = await transcribe_audio(audio_bytes)

    if not text_content:
        raise ValueError("No text content to process")

    # 2. Embed user message
    embedding = await embed_text(text_content)

    # 3. Store user message with embedding
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=text_content,
        embedding=embedding,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # 4. Retrieve context
    semantic_ctx = await retrieve_context(db, conversation_id, embedding)
    recent = await get_recent_messages(db, conversation_id)
    system_prompt = await get_system_prompt(db, conversation_id, redis_client)

    # 5. Build prompt and call LLM
    messages = await build_messages(system_prompt, semantic_ctx, recent, text_content)
    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    reply_text = completion.choices[0].message.content

    # 6. Embed and store assistant message
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

    # 7. TTS if requested
    audio_url = None
    if reply_with_voice:
        try:
            audio_url = await synthesize_speech(reply_text)
        except Exception:
            audio_url = None  # TTS failure: return text only

    return {
        "user_message_id": user_msg.id,
        "content": reply_text,
        "assistant_message_id": assistant_msg.id,
        "audio_url": audio_url,
    }
