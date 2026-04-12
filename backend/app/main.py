from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
from app.voice.router import router as voice_router
from app.chat.router import router as chat_router
from app.admin.router import router as admin_router

app = FastAPI(title="AI Speaker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
