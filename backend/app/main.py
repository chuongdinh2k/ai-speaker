from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
from app.voice.router import router as voice_router
from app.chat.router import router as chat_router
from app.admin.router import router as admin_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
