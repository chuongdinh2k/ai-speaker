# Design: WebSocket → REST API Chat

**Date:** 2026-04-11

## Overview

Replace the existing WebSocket-based chat with standard HTTP REST endpoints. Users send messages step by step (request/response). Voice input uses hold-to-record: release triggers transcription, then the AI reply call. Both text and voice are supported. User messages are stored and displayed immediately. A "AI is thinking..." indicator shows while the request is in flight.

---

## What Changes

| Area | Before | After |
|---|---|---|
| Transport | WebSocket `/ws/chat/{conversation_id}` | HTTP POST `/chat/send` |
| Voice delivery | base64 JSON over WebSocket | multipart FormData to `/voice/transcribe` |
| Auth (chat) | JWT as query param `?token=...` | JWT as Bearer header |
| Connection state | `connected`/`Disconnected` UI | Removed (stateless HTTP) |
| Loading state | None | `loading` bool, "AI is thinking..." bubble |

---

## Backend

### Remove
- `GET /ws/chat/{conversation_id}` WebSocket endpoint and all WebSocket handling code in `chat/router.py`

### Add
**`POST /chat/send`**
- Auth: `Depends(get_current_user)` (Bearer JWT)
- Request body:
  ```json
  {
    "conversation_id": "uuid",
    "content": "string",
    "reply_with_voice": true
  }
  ```
- Response:
  ```json
  {
    "user_message": { "id": "uuid", "content": "string" },
    "assistant_message": { "id": "uuid", "content": "string", "audio_url": "string | null" }
  }
  ```
- Reuses existing `handle_chat_message()` service — no pipeline changes
- Returns HTTP 200 on success, 422 on validation error, 500 on LLM/TTS failure

### Keep
- `POST /voice/transcribe` — unchanged
- `handle_chat_message()` service — unchanged
- All RAG, embedding, TTS internals — unchanged

---

## Frontend

### `useChat.ts` (rewrite)

State:
- `messages: ChatMessage[]`
- `loading: boolean`
- `error: string | null`

Functions:
- `sendText(content: string, replyWithVoice: boolean)`
  1. Append user message to `messages` immediately
  2. Set `loading = true`
  3. POST `/chat/send`
  4. On success: append assistant message, set `loading = false`
  5. On error: set error banner, set `loading = false` (user message stays)

- `sendVoice(audioBlob: Blob, replyWithVoice: boolean)`
  1. POST `audioBlob` to `/voice/transcribe` (FormData)
  2. On transcription success: append user message with transcribed text
  3. Set `loading = true`
  4. POST `/chat/send` with transcribed text
  5. On success: append assistant message, set `loading = false`
  6. On transcription error: show error banner, no user bubble added

No WebSocket, no `connected` state.

### `MessageInput.tsx` (minor changes)

- `disabled` prop driven by `loading` (was `connected`)
- Pass raw `Blob` to `sendVoice` instead of base64 string
- Hold-to-record interaction (`onMouseDown`/`onMouseUp`) unchanged
- Voice button label: "Recording..." (red) while recording, "Voice" otherwise — already works

### `ChatPage.tsx` (minor changes)

- Remove `connected`/`Disconnected` status badge
- When `loading === true`: render an animated "AI is thinking..." bubble at bottom of message list
- Bubble style: matches assistant bubble, with pulsing dots animation (CSS)
- When `loading` becomes false: bubble disappears, replaced by actual assistant message

---

## UX Flow

**Text:**
```
User types → Send → user bubble appears → "AI thinking..." → response → assistant bubble
```

**Voice:**
```
Hold button → recording (red) → release → transcribe → user bubble appears → "AI thinking..." → response → assistant bubble
```

---

## Error Handling

| Failure | Behavior |
|---|---|
| Transcription fails | Error banner shown, no user bubble added, `loading` stays false |
| `/chat/send` fails | Error banner shown, user bubble stays visible |
| TTS fails | Backend falls back to text-only (existing behavior), `audio_url: null` |
| Double-send | Send/Voice buttons disabled while `loading === true` |

---

## Out of Scope

- Streaming responses (Phase 2)
- Message history loading on page open (existing behavior unchanged)
- Any changes to RAG pipeline, embeddings, or TTS internals
