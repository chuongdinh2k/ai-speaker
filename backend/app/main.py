from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
