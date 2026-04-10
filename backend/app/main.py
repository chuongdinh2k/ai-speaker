from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

@app.get("/health")
async def health():
    return {"status": "ok"}
