from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.voice.service import transcribe_audio
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])

class TranscribeResponse(BaseModel):
    text: str

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    try:
        audio_bytes = await file.read()
        text = await transcribe_audio(audio_bytes, file.filename or "audio.webm")
        return TranscribeResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
