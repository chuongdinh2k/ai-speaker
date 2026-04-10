# Phase 1 Design: AI Speaker Chat App

## Overview

An app where users log in and chat with an AI bot across various topics. The bot responds with text or voice (TTS). Each conversation retains full history with RAG-based context retrieval. Users can delete conversations.

**Stack:** FastAPI (Python), React + Tailwind, Postgres + pgvector, Redis, OpenAI (GPT-4o, Whisper, TTS), LangChain, WebSockets, Docker Compose

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│         (Tailwind, REST + WebSocket client)         │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP / WS
┌─────────────────────▼───────────────────────────────┐
│                  FastAPI Backend                     │
│  ┌──────────┐ ┌──────────┐ ┌───────┐ ┌──────────┐  │
│  │   auth   │ │  topics  │ │ chat  │ │  voice   │  │
│  └──────────┘ └──────────┘ └───┬───┘ └──────────┘  │
│                                │ LangChain + RAG    │
└────────────────────────────────┼────────────────────┘
                    ┌────────────┼──────────┐
              ┌─────▼──┐   ┌────▼───┐  ┌───▼───┐
              │Postgres│   │pgvector│  │ Redis │
              │(users, │   │(message│  │(cache)│
              │convos, │   │embedds)│  │       │
              │msgs...)│   └────────┘  └───────┘
              └────────┘
                    │
              ┌─────▼──────┐
              │  OpenAI    │
              │ (LLM + STT │
              │  + TTS)    │
              └────────────┘
```

- Single FastAPI process with 4 internal modules: `auth`, `topics`, `chat`, `voice`
- WebSocket endpoint inside FastAPI: `/ws/chat/{conversation_id}`
- Postgres for relational data + pgvector extension for message embeddings
- Redis for session cache and conversation context cache
- OpenAI: GPT-4o for chat, Whisper for STT, TTS API for voice responses

---

## Data Models

### users
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| email | text | unique |
| password_hash | text | |
| created_at | timestamp | |

### topics
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| name | text | |
| description | text | |
| system_prompt | text | editable by admin via API |
| created_at | timestamp | |

### conversations
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users |
| topic_id | uuid | FK topics |
| created_at | timestamp | |
| deleted_at | timestamp | nullable, soft delete |

Unique constraint on `(user_id, topic_id)` — one conversation per user per topic.

### messages
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| conversation_id | uuid | FK conversations |
| role | enum | `user` or `assistant` |
| content | text | text content |
| audio_url | text | nullable, path to TTS audio file |
| embedding | vector | pgvector, for RAG retrieval |
| created_at | timestamp | |

### prompt_templates
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| topic_id | uuid | FK topics |
| content | text | |
| version | int | for future audit/versioning |
| created_at | timestamp | |

### subscriptions
| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users |
| plan | text | stub for Phase 2 |
| status | text | stub for Phase 2 |

---

## API Endpoints

### Auth
- `POST /auth/register` — email + password registration
- `POST /auth/login` — returns JWT
- `POST /auth/logout`

### Topics
- `GET /topics` — list all topics
- `POST /topics` (admin) — create topic
- `PUT /topics/{id}` (admin) — update topic + system prompt

### Conversations
- `GET /conversations` — list user's conversations
- `POST /conversations` — create/get conversation for a topic (upsert by user_id + topic_id)
- `DELETE /conversations/{id}` — soft delete conversation + cascade delete messages

### Chat
- `WebSocket /ws/chat/{conversation_id}?token=<jwt>`
  - Client sends: `{ "type": "text", "content": "...", "reply_with_voice": true|false }` or `{ "type": "voice", "audio_base64": "...", "reply_with_voice": true|false }`
  - Server responds: `{ "type": "message", "content": "...", "audio_url": null | "..." }`
  - Server errors: `{ "type": "error", "code": "...", "message": "..." }`

### Voice
- `POST /voice/transcribe` — upload audio → returns transcribed text (Whisper)
- TTS is called internally during chat; audio URL returned in WebSocket message

### Admin
- `PUT /admin/topics/{id}/prompt` — update system prompt for a topic

---

## Chat Flow (RAG Pipeline)

```
1. Receive message via WebSocket (text or voice)
   └─ if voice: POST to Whisper STT → get text

2. Embed the incoming text (OpenAI embeddings)
   └─ store embedding in pgvector (messages table)

3. Retrieve context
   ├─ Semantic search: top-K similar messages from this conversation (pgvector cosine similarity)
   └─ Recent window: last N messages (recency anchor)

4. Build prompt
   ├─ system prompt from topic (prompt_templates)
   ├─ retrieved semantic context messages
   └─ recent message window

5. Call OpenAI LLM (GPT-4o)
   └─ get text response

6. Store assistant message + embed it
   └─ save to messages table with embedding

7. If message included reply_with_voice: true:
   └─ call OpenAI TTS → store audio file (UUID filename) → get audio_url

8. Send WS response to client
   └─ { content: "...", audio_url: "..." | null }
```

Redis caches the conversation's recent message window and topic system prompt to avoid repeated DB reads on every message.

---

## Error Handling

- WebSocket errors return structured JSON: `{ "type": "error", "code": "...", "message": "..." }`
- HTTP errors follow standard status codes with `{ "detail": "..." }` body (FastAPI default)
- OpenAI failures: catch API errors, return user-friendly WS error, log full error server-side
- STT failure: return WS error asking user to retry
- TTS failure: fall back gracefully — return text-only response, no audio_url

---

## Security

- JWT required on all endpoints except `/auth/*`
- WebSocket auth: JWT passed as query param on connect (`?token=...`)
- Admin endpoints protected by role claim in JWT
- Audio files stored on Docker volume with UUID filenames (not guessable)

---

## Non-Functional Requirements

- **Performance:** Non-streaming responses for Phase 1. Redis reduces redundant DB reads.
- **Cost:** Embeddings stored in pgvector (no re-embedding). Redis caches prompts and recent windows.
- **Extensibility:** Module boundaries (`auth/`, `chat/`, `topics/`, `voice/`) enable Phase 2 microservice extraction.

---

## Docker Compose (End of Phase 1)

Services:
- `api` — FastAPI backend (built from local Dockerfile)
- `frontend` — React app (built from local Dockerfile)
- `postgres` — `pgvector/pgvector` image with pgvector extension
- `redis` — default Redis image

Configuration via `.env` file: OpenAI API key, JWT secret, database URL, Redis URL.

---

## Out of Scope (Phase 2)

- Streaming AI responses
- OAuth/social login
- User-editable prompts
- Task queuing (Redis queues for LLM/TTS jobs)
- User ranking, credits, chat modes
- Contributor knowledge bases
- Microservice extraction
