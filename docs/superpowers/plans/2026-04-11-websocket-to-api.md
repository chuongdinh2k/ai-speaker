# WebSocket → REST API Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace WebSocket-based chat with HTTP REST endpoints, add hold-to-record voice UX, display user messages immediately, and show an "AI is thinking..." indicator while waiting for responses.

**Architecture:** The backend WebSocket endpoint is replaced by a single `POST /chat/send` endpoint that accepts text and returns both user and assistant message data. The frontend hook is rewritten to use two sequential HTTP calls for voice (transcribe → send), and one call for text. Loading state drives a pulsing "AI is thinking..." bubble in the UI.

**Tech Stack:** FastAPI + Pydantic (backend), React + Axios + Tailwind (frontend), existing `handle_chat_message()` service (unchanged)

---

## File Map

**Backend — modify:**
- `backend/app/schemas/chat.py` — replace WS schemas with REST request/response schemas
- `backend/app/chat/router.py` — replace WebSocket handler with `POST /chat/send`

**Backend — unchanged:**
- `backend/app/chat/service.py` — `handle_chat_message()` reused as-is
- `backend/app/voice/router.py` — `POST /voice/transcribe` unchanged
- `backend/app/main.py` — no changes needed

**Frontend — rewrite:**
- `frontend/src/hooks/useChat.ts` — remove WebSocket, add HTTP-based sendText/sendVoice with loading state

**Frontend — modify:**
- `frontend/src/components/MessageInput.tsx` — pass Blob (not base64), disabled driven by loading
- `frontend/src/pages/ChatPage.tsx` — remove connected badge, add thinking bubble
- `frontend/src/api/endpoints.ts` — add chatApi with transcribe and send functions

---

## Task 1: Update backend chat schemas

**Files:**
- Modify: `backend/app/schemas/chat.py`

- [ ] **Step 1: Replace the file contents**

```python
from uuid import UUID
from pydantic import BaseModel

class ChatSendRequest(BaseModel):
    conversation_id: UUID
    content: str
    reply_with_voice: bool = False

class MessageOut(BaseModel):
    id: UUID
    content: str
    audio_url: str | None = None

class ChatSendResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
```

- [ ] **Step 2: Verify no import errors**

```bash
cd backend && python -c "from app.schemas.chat import ChatSendRequest, ChatSendResponse, MessageOut; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/chat.py
git commit -m "refactor: replace WebSocket schemas with REST chat schemas"
```

---

## Task 2: Rewrite backend chat router

**Files:**
- Modify: `backend/app/chat/router.py`

- [ ] **Step 1: Rewrite the router**

```python
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis
from app.auth.dependencies import get_current_user
from app.chat.service import handle_chat_message
from app.schemas.chat import ChatSendRequest, ChatSendResponse, MessageOut

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    body: ChatSendRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    try:
        result = await handle_chat_message(
            db, redis_client, body.conversation_id,
            text_content=body.content,
            audio_bytes=None,
            reply_with_voice=body.reply_with_voice,
        )
    except Exception:
        import logging
        logging.exception("Chat error")
        raise HTTPException(status_code=500, detail="An error occurred. Please try again.")

    return ChatSendResponse(
        user_message=MessageOut(id=uuid4(), content=body.content),
        assistant_message=MessageOut(
            id=uuid4(),
            content=result["content"],
            audio_url=result["audio_url"],
        ),
    )
```

- [ ] **Step 2: Verify the app starts without errors**

```bash
cd backend && python -c "from app.chat.router import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/chat/router.py
git commit -m "feat: replace WebSocket chat with POST /chat/send endpoint"
```

---

## Task 3: Add chat API functions to frontend endpoints

**Files:**
- Modify: `frontend/src/api/endpoints.ts`

- [ ] **Step 1: Add chatApi to the endpoints file**

Add these exports at the bottom of `frontend/src/api/endpoints.ts`:

```typescript
export interface ChatSendResponse {
  user_message: { id: string; content: string }
  assistant_message: { id: string; content: string; audio_url: string | null }
}

export const chatApi = {
  send: (conversation_id: string, content: string, reply_with_voice: boolean) =>
    client.post<ChatSendResponse>("/chat/send", { conversation_id, content, reply_with_voice }),

  transcribe: (audioBlob: Blob) => {
    const form = new FormData()
    form.append("file", audioBlob, "audio.webm")
    return client.post<{ text: string }>("/voice/transcribe", form)
  },
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/endpoints.ts
git commit -m "feat: add chatApi.send and chatApi.transcribe to endpoints"
```

---

## Task 4: Rewrite useChat hook

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Rewrite the hook**

```typescript
import { useState, useCallback } from "react"
import { chatApi } from "../api/endpoints"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.send(conversationId, content, replyWithVoice)
      const { assistant_message } = res.data
      setMessages(prev => [...prev, {
        role: "assistant",
        content: assistant_message.content,
        audio_url: assistant_message.audio_url,
      }])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  const sendVoice = useCallback(async (audioBlob: Blob, replyWithVoice: boolean) => {
    setError(null)
    try {
      const transcribeRes = await chatApi.transcribe(audioBlob)
      const transcribedText = transcribeRes.data.text
      setMessages(prev => [...prev, { role: "user", content: transcribedText }])
      setLoading(true)
      try {
        const res = await chatApi.send(conversationId, transcribedText, replyWithVoice)
        const { assistant_message } = res.data
        setMessages(prev => [...prev, {
          role: "assistant",
          content: assistant_message.content,
          audio_url: assistant_message.audio_url,
        }])
      } catch {
        setError("Failed to get a response. Please try again.")
      } finally {
        setLoading(false)
      }
    } catch {
      setError("Transcription failed. Please try again.")
    }
  }, [conversationId])

  return { messages, loading, error, sendText, sendVoice }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "refactor: rewrite useChat to use HTTP instead of WebSocket"
```

---

## Task 5: Update MessageInput to pass Blob and use loading

**Files:**
- Modify: `frontend/src/components/MessageInput.tsx`

- [ ] **Step 1: Update the component**

```typescript
import { useState, useRef } from "react"

interface Props {
  onSendText: (text: string, replyWithVoice: boolean) => void
  onSendVoice: (blob: Blob, replyWithVoice: boolean) => void
  disabled: boolean
}

export default function MessageInput({ onSendText, onSendVoice, disabled }: Props) {
  const [text, setText] = useState("")
  const [replyWithVoice, setReplyWithVoice] = useState(false)
  const [recording, setRecording] = useState(false)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const handleSend = () => {
    if (!text.trim()) return
    onSendText(text.trim(), replyWithVoice)
    setText("")
  }

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRef.current = new MediaRecorder(stream)
    chunksRef.current = []
    mediaRef.current.ondataavailable = e => chunksRef.current.push(e.data)
    mediaRef.current.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" })
      onSendVoice(blob, replyWithVoice)
      stream.getTracks().forEach(t => t.stop())
    }
    mediaRef.current.start()
    setRecording(true)
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="flex items-center gap-2 p-4 border-t bg-white">
      <input
        value={text} onChange={e => setText(e.target.value)}
        onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
        placeholder="Type a message..." disabled={disabled}
        className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <button onClick={handleSend} disabled={disabled || !text.trim()}
        className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
        Send
      </button>
      <button
        onMouseDown={startRecording} onMouseUp={stopRecording}
        disabled={disabled}
        className={`px-4 py-2 rounded text-sm ${recording ? "bg-red-500 text-white" : "bg-gray-200 text-gray-700"} hover:opacity-80 disabled:opacity-50`}>
        {recording ? "Recording..." : "Voice"}
      </button>
      <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
        <input type="checkbox" checked={replyWithVoice} onChange={e => setReplyWithVoice(e.target.checked)} />
        Voice reply
      </label>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MessageInput.tsx
git commit -m "refactor: MessageInput passes Blob to onSendVoice, disabled by loading"
```

---

## Task 6: Update ChatPage with thinking bubble and remove WS status

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: Rewrite ChatPage**

```typescript
import { useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, loading, error, sendText, sendVoice } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
      </div>
      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2">{error}</div>}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((m, i) => <MessageBubble key={i} message={m} />)}
        {loading && (
          <div className="flex justify-start mb-2">
            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-500 flex items-center gap-1 shadow-sm">
              <span className="animate-bounce [animation-delay:0ms]">●</span>
              <span className="animate-bounce [animation-delay:150ms]">●</span>
              <span className="animate-bounce [animation-delay:300ms]">●</span>
              <span className="ml-2">AI is thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <MessageInput onSendText={sendText} onSendVoice={sendVoice} disabled={loading} />
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ChatPage.tsx
git commit -m "feat: add AI thinking bubble, remove WebSocket status indicator"
```

---

## Task 7: Manual smoke test

- [ ] **Step 1: Start services**

```bash
cd /Users/chuong/Documents/learning/AI-speaker && docker compose up --build
```

- [ ] **Step 2: Test text message flow**

1. Open `http://localhost:5173` in a browser
2. Log in and navigate to a topic → open a conversation
3. Type a message and press Send
4. Verify: user message bubble appears immediately
5. Verify: "AI is thinking..." pulsing dots appear
6. Verify: dots disappear and assistant message appears when response arrives

- [ ] **Step 3: Test voice message flow**

1. Hold the Voice button — verify it turns red and shows "Recording..."
2. Release the button
3. Verify: user message bubble appears with transcribed text
4. Verify: "AI is thinking..." indicator appears
5. Verify: assistant message appears when response arrives

- [ ] **Step 4: Test voice reply toggle**

1. Check "Voice reply" checkbox
2. Send a message
3. Verify: assistant message has audio that plays automatically (check MessageBubble behavior)

- [ ] **Step 5: Test error state**

1. Stop the backend (Ctrl+C on the api container)
2. Send a text message
3. Verify: user bubble appears, then error banner shows, loading stops

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: complete WebSocket → REST API migration with voice UX"
```
