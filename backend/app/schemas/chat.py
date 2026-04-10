from pydantic import BaseModel

class WSIncomingText(BaseModel):
    type: str  # "text" or "voice"
    content: str | None = None
    audio_base64: str | None = None
    reply_with_voice: bool = False

class WSOutgoingMessage(BaseModel):
    type: str  # "message" or "error"
    content: str | None = None
    audio_url: str | None = None
    code: str | None = None
    message: str | None = None
