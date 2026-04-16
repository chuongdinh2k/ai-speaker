# UI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user profile page, global vocabulary tracking page, chat auto-play audio + hide/show text + topic name header, sticky voice reply default, and mobile-first responsive design.

**Architecture:** Backend-first — add `avatar_url` to users, enrich `/auth/me`, add global vocab endpoint, extend conversations to return `topic_name`. Then build frontend pages and update existing components.

**Tech Stack:** FastAPI + SQLAlchemy (async) + Alembic (backend); React + TypeScript + Tailwind CSS + React Router (frontend)

---

## File Map

### Backend — Create
- `backend/alembic/versions/004_add_avatar_url.py` — migration adding `avatar_url` to `users`

### Backend — Modify
- `backend/app/models/user.py` — add `avatar_url` field
- `backend/app/schemas/auth.py` — add `avatar_url`, `level`, `total_messages` to `UserResponse`
- `backend/app/auth/router.py` — update `/auth/me` to return enriched profile
- `backend/app/schemas/conversation.py` — add `topic_name: str` to `ConversationResponse`
- `backend/app/conversations/service.py` — join `topics` table in `list_conversations`
- `backend/app/conversations/router.py` — pass topic_name through
- `backend/app/schemas/vocabulary.py` — add `VocabularyWithTopicResponse` schema
- `backend/app/vocabularies/router.py` — add `GET /vocabularies/all` endpoint
- `backend/app/vocabularies/service.py` — add `list_all_vocabularies` function

### Frontend — Create
- `frontend/src/pages/ProfilePage.tsx` — user profile card
- `frontend/src/pages/GlobalVocabularyPage.tsx` — all-vocab read-only page
- `frontend/src/hooks/useProfile.ts` — fetch `/auth/me`

### Frontend — Modify
- `frontend/src/api/endpoints.ts` — add `authApi.me()`, `vocabularyApi.listAll()`, update `Conversation` type, add `UserProfile` type
- `frontend/src/App.tsx` — add `/profile` and `/vocabulary` routes
- `frontend/src/pages/TopicsPage.tsx` — add nav links to profile + vocabulary; responsive grid
- `frontend/src/pages/ChatPage.tsx` — show topic name in header, wire auto-play, hide/show text
- `frontend/src/hooks/useChat.ts` — expose `topicName`; return `lastAssistantAudioUrl` for auto-play
- `frontend/src/components/MessageBubble.tsx` — add hide/show text toggle
- `frontend/src/components/MessageInput.tsx` — sticky voice reply (localStorage, default true)

---

## Task 1: Alembic migration — add `avatar_url` to users

**Files:**
- Create: `backend/alembic/versions/004_add_avatar_url.py`
- Modify: `backend/app/models/user.py`

- [ ] **Step 1: Write the migration file**

```python
# backend/alembic/versions/004_add_avatar_url.py
"""add avatar_url to users

Revision ID: 004
Revises: 003
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('avatar_url', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
```

- [ ] **Step 2: Add `avatar_url` to the User model**

In `backend/app/models/user.py`, add after the `level` field:

```python
avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Also add `from sqlalchemy import String, DateTime, Text` (replace existing `String, DateTime` import).

- [ ] **Step 3: Run the migration**

```bash
cd backend && alembic upgrade head
```

Expected output ends with: `Running upgrade 003 -> 004`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/004_add_avatar_url.py backend/app/models/user.py
git commit -m "feat: add avatar_url column to users table"
```

---

## Task 2: Enrich `/auth/me` — return `avatar_url`, `level`, `total_messages`

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/auth/router.py`

- [ ] **Step 1: Update `UserResponse` schema**

Replace the entire content of `backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    level: str = "A2"
    avatar_url: str | None = None
    total_messages: int = 0
```

- [ ] **Step 2: Update `/auth/me` handler to compute `total_messages`**

Replace the `me` endpoint in `backend/app/auth/router.py`. Add imports at top:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.models.conversation import Conversation
```

Replace the `me` endpoint:

```python
@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Fetch user row for avatar_url and level
    result = await db.execute(select(User).where(User.id == user["sub"]))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count user messages across all their conversations
    count_result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == db_user.id,
            Message.role == "user",
        )
    )
    total_messages = count_result.scalar_one() or 0

    return UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        role=db_user.role,
        level=db_user.level,
        avatar_url=db_user.avatar_url,
        total_messages=total_messages,
    )
```

Note: the `User.id` is a UUID but `user["sub"]` from JWT is a string — use `UUID(user["sub"])` in the where clause:

```python
from uuid import UUID
# in the handler:
result = await db.execute(select(User).where(User.id == UUID(user["sub"])))
```

- [ ] **Step 3: Verify the endpoint starts without errors**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Expected: server starts, no import errors. Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/auth/router.py
git commit -m "feat: enrich /auth/me with level, avatar_url, total_messages"
```

---

## Task 3: Add `topic_name` to conversations list

**Files:**
- Modify: `backend/app/schemas/conversation.py`
- Modify: `backend/app/conversations/service.py`
- Modify: `backend/app/conversations/router.py`

- [ ] **Step 1: Update `ConversationResponse` schema**

Replace `backend/app/schemas/conversation.py`:

```python
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class ConversationCreate(BaseModel):
    topic_id: UUID


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    topic_name: str = ""
    created_at: datetime
    message_count: int = 0
```

- [ ] **Step 2: Update `list_conversations` service to join topics**

In `backend/app/conversations/service.py`, add import at top:

```python
from app.models.topic import Topic
```

Replace the `list_conversations` function:

```python
async def list_conversations(db: AsyncSession, user_id: UUID) -> list[dict]:
    msg_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Conversation, Topic.name.label("topic_name"), msg_count.label("message_count"))
        .join(Topic, Conversation.topic_id == Topic.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    rows = result.all()
    out = []
    for conv, topic_name, count in rows:
        out.append({
            "id": conv.id,
            "topic_id": conv.topic_id,
            "topic_name": topic_name,
            "created_at": conv.created_at,
            "message_count": count,
        })
    return out
```

- [ ] **Step 3: Verify server starts cleanly**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Expected: no errors. Stop with Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/conversation.py backend/app/conversations/service.py
git commit -m "feat: include topic_name in conversations list response"
```

---

## Task 4: Add `GET /vocabularies/all` endpoint

**Files:**
- Modify: `backend/app/schemas/vocabulary.py`
- Modify: `backend/app/vocabularies/service.py`
- Modify: `backend/app/vocabularies/router.py`

- [ ] **Step 1: Add `VocabularyWithTopicResponse` schema**

In `backend/app/schemas/vocabulary.py`, append:

```python
class VocabularyWithTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    topic_id: UUID
    topic_name: str
    word: str
    added_at: datetime
    usage_count: int
    is_active: bool
```

- [ ] **Step 2: Add `list_all_vocabularies` service function**

In `backend/app/vocabularies/service.py`, add import at top:

```python
from app.models.topic import Topic
```

Append the new function:

```python
async def list_all_vocabularies(db: AsyncSession, user_id: UUID) -> list[dict]:
    from app.models.topic import Topic
    result = await db.execute(
        select(UserVocabulary, Topic.name.label("topic_name"))
        .join(Topic, UserVocabulary.topic_id == Topic.id)
        .where(UserVocabulary.user_id == user_id)
        .order_by(Topic.name, UserVocabulary.added_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": vocab.id,
            "user_id": vocab.user_id,
            "topic_id": vocab.topic_id,
            "topic_name": topic_name,
            "word": vocab.word,
            "added_at": vocab.added_at,
            "usage_count": vocab.usage_count,
            "is_active": vocab.is_active,
        }
        for vocab, topic_name in rows
    ]
```

- [ ] **Step 3: Add `GET /vocabularies/all` route**

In `backend/app/vocabularies/router.py`, add import:

```python
from app.schemas.vocabulary import VocabularyCreate, VocabularyResponse, VocabularyWithTopicResponse
from app.vocabularies.service import (
    list_vocabularies,
    list_all_vocabularies,
    add_vocabulary,
    delete_vocabulary,
    activate_vocabulary,
    deactivate_vocabulary,
)
```

Add the new route **before** the existing `GET ""` route (order matters — more specific path first):

```python
@router.get("/all", response_model=list[VocabularyWithTopicResponse])
async def get_all_vocabularies(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_all_vocabularies(db, UUID(user["sub"]))
    return rows
```

- [ ] **Step 4: Verify server starts cleanly**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Expected: no errors. Stop with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/vocabulary.py backend/app/vocabularies/service.py backend/app/vocabularies/router.py
git commit -m "feat: add GET /vocabularies/all endpoint with topic names"
```

---

## Task 5: Update frontend API types and client

**Files:**
- Modify: `frontend/src/api/endpoints.ts`

- [ ] **Step 1: Replace `endpoints.ts` with updated types and new calls**

Replace the full content of `frontend/src/api/endpoints.ts`:

```typescript
import client from "./client"

export interface Topic {
  id: string
  name: string
  description: string | null
  system_prompt: string | null
}

export interface Conversation {
  id: string
  topic_id: string
  topic_name: string
  created_at: string
  message_count: number
}

export interface UserProfile {
  id: string
  email: string
  role: string
  level: string
  avatar_url: string | null
  total_messages: number
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    client.post<{ access_token: string }>("/auth/login", { email, password }),
  logout: () => client.post("/auth/logout"),
  me: () => client.get<UserProfile>("/auth/me"),
}

export const topicsApi = {
  list: () => client.get<Topic[]>("/topics"),
}

export const conversationsApi = {
  list: () => client.get<Conversation[]>("/conversations"),
  create: (topic_id: string) => client.post<Conversation>("/conversations", { topic_id }),
  delete: (id: string) => client.delete(`/conversations/${id}`),
}

export interface MessageOut {
  id: string
  role: "user" | "assistant"
  content: string
  audio_url: string | null
}

export interface ChatSendResponse {
  user_message: MessageOut
  assistant_message: MessageOut
  active_vocab: string[]
}

export interface ChatHistoryResponse {
  messages: MessageOut[]
  next_cursor: string | null
}

export const chatApi = {
  history: (conversation_id: string, cursor?: string) =>
    client.get<ChatHistoryResponse>(`/chat/${conversation_id}/messages`, {
      params: cursor ? { cursor } : undefined,
    }),

  sendText: (conversation_id: string, content: string, reply_with_voice: boolean) => {
    const form = new FormData()
    form.append("conversation_id", conversation_id)
    form.append("content", content)
    form.append("reply_with_voice", String(reply_with_voice))
    return client.post<ChatSendResponse>("/chat/send", form)
  },

  sendAudio: (conversation_id: string, audioBlob: Blob, reply_with_voice: boolean) => {
    const form = new FormData()
    form.append("conversation_id", conversation_id)
    form.append("audio", audioBlob, "audio.webm")
    form.append("reply_with_voice", String(reply_with_voice))
    return client.post<ChatSendResponse>("/chat/send", form)
  },
}

export interface VocabularyItem {
  id: string
  user_id: string
  topic_id: string
  word: string
  added_at: string
  usage_count: number
  is_active: boolean
}

export interface VocabularyItemWithTopic extends VocabularyItem {
  topic_name: string
}

export const vocabularyApi = {
  list: (topic_id: string) =>
    client.get<VocabularyItem[]>("/vocabularies", { params: { topic_id } }),
  listAll: () =>
    client.get<VocabularyItemWithTopic[]>("/vocabularies/all"),
  add: (topic_id: string, word: string) =>
    client.post<VocabularyItem>("/vocabularies", { topic_id, word }),
  delete: (id: string) => client.delete(`/vocabularies/${id}`),
  activate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/activate`),
  deactivate: (id: string) => client.patch<VocabularyItem>(`/vocabularies/${id}/deactivate`),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/endpoints.ts
git commit -m "feat: add UserProfile type, authApi.me, vocabularyApi.listAll, topic_name on Conversation"
```

---

## Task 6: Build `ProfilePage`

**Files:**
- Create: `frontend/src/pages/ProfilePage.tsx`
- Create: `frontend/src/hooks/useProfile.ts`

- [ ] **Step 1: Create `useProfile` hook**

Create `frontend/src/hooks/useProfile.ts`:

```typescript
import { useState, useEffect } from "react"
import { authApi, type UserProfile } from "../api/endpoints"

export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    authApi.me()
      .then(r => setProfile(r.data))
      .catch(() => setError("Failed to load profile"))
      .finally(() => setLoading(false))
  }, [])

  return { profile, loading, error }
}
```

- [ ] **Step 2: Create `ProfilePage`**

Create `frontend/src/pages/ProfilePage.tsx`:

```typescript
import { useNavigate } from "react-router-dom"
import { useProfile } from "../hooks/useProfile"

function getInitials(email: string): string {
  return email.split("@")[0].slice(0, 2).toUpperCase()
}

function getAvatarColor(email: string): string {
  const colors = [
    "bg-blue-500", "bg-purple-500", "bg-green-500",
    "bg-yellow-500", "bg-red-500", "bg-indigo-500",
    "bg-pink-500", "bg-teal-500",
  ]
  let hash = 0
  for (let i = 0; i < email.length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

const LEVEL_COLORS: Record<string, string> = {
  A1: "bg-gray-100 text-gray-600",
  A2: "bg-blue-100 text-blue-700",
  B1: "bg-green-100 text-green-700",
  B2: "bg-yellow-100 text-yellow-700",
  C1: "bg-orange-100 text-orange-700",
  C2: "bg-red-100 text-red-700",
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const { profile, loading, error } = useProfile()

  return (
    <div className="min-h-dvh bg-gray-50 px-4 py-6 max-w-lg mx-auto">
      <button
        onClick={() => navigate("/topics")}
        className="text-sm text-blue-600 hover:underline mb-6 inline-block"
      >
        ← Back
      </button>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {profile && (
        <div className="bg-white rounded-2xl shadow-sm border p-6 space-y-6">
          {/* Avatar */}
          <div className="flex flex-col items-center gap-3">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt="Avatar"
                className="w-20 h-20 rounded-full object-cover"
              />
            ) : (
              <div className={`w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl font-bold ${getAvatarColor(profile.email)}`}>
                {getInitials(profile.email)}
              </div>
            )}
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${LEVEL_COLORS[profile.level] ?? "bg-gray-100 text-gray-600"}`}>
              {profile.level}
            </span>
          </div>

          {/* Details */}
          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Email</p>
              <p className="text-sm font-medium text-gray-800 break-all">{profile.email}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">CEFR Level</p>
              <p className="text-sm font-medium text-gray-800">{profile.level}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Messages Sent</p>
              <p className="text-2xl font-bold text-blue-600">{profile.total_messages}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Role</p>
              <p className="text-sm font-medium text-gray-800 capitalize">{profile.role}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useProfile.ts frontend/src/pages/ProfilePage.tsx
git commit -m "feat: add ProfilePage with avatar initials fallback and user stats"
```

---

## Task 7: Build `GlobalVocabularyPage`

**Files:**
- Create: `frontend/src/pages/GlobalVocabularyPage.tsx`

- [ ] **Step 1: Create `GlobalVocabularyPage`**

Create `frontend/src/pages/GlobalVocabularyPage.tsx`:

```typescript
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { vocabularyApi, type VocabularyItemWithTopic } from "../api/endpoints"

export default function GlobalVocabularyPage() {
  const navigate = useNavigate()
  const [words, setWords] = useState<VocabularyItemWithTopic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    vocabularyApi.listAll()
      .then(r => setWords(r.data))
      .catch(() => setError("Failed to load vocabulary"))
      .finally(() => setLoading(false))
  }, [])

  // Group by topic_name
  const grouped = words.reduce<Record<string, VocabularyItemWithTopic[]>>((acc, item) => {
    if (!acc[item.topic_name]) acc[item.topic_name] = []
    acc[item.topic_name].push(item)
    return acc
  }, {})

  return (
    <div className="min-h-dvh bg-gray-50 px-4 py-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
        <h1 className="text-xl font-bold">My Vocabulary</h1>
        <span className="ml-auto text-sm text-gray-400">{words.length} words</span>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {!loading && words.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-16">No vocabulary yet. Add words from a topic page.</p>
      )}

      <div className="space-y-6">
        {Object.entries(grouped).map(([topicName, items]) => (
          <div key={topicName}>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">
              {topicName}
            </h2>
            <div className="space-y-2">
              {items.map(item => (
                <div
                  key={item.id}
                  className="bg-white border rounded-xl px-4 py-3 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-800">{item.word}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Added {new Date(item.added_at).toLocaleDateString()} · Used {item.usage_count}×
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    item.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-400"
                  }`}>
                    {item.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GlobalVocabularyPage.tsx
git commit -m "feat: add GlobalVocabularyPage grouped by topic"
```

---

## Task 8: Add new routes to `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update `App.tsx`**

Replace the full content of `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import LoginPage from "./pages/LoginPage"
import TopicsPage from "./pages/TopicsPage"
import ChatPage from "./pages/ChatPage"
import VocabularyPage from "./pages/VocabularyPage"
import ProfilePage from "./pages/ProfilePage"
import GlobalVocabularyPage from "./pages/GlobalVocabularyPage"

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token")
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/topics" element={<PrivateRoute><TopicsPage /></PrivateRoute>} />
        <Route path="/chat/:conversationId" element={<PrivateRoute><ChatPage /></PrivateRoute>} />
        <Route path="/topics/:topicId/vocabulary" element={<PrivateRoute><VocabularyPage /></PrivateRoute>} />
        <Route path="/profile" element={<PrivateRoute><ProfilePage /></PrivateRoute>} />
        <Route path="/vocabulary" element={<PrivateRoute><GlobalVocabularyPage /></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/topics" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add /profile and /vocabulary routes"
```

---

## Task 9: Update `TopicsPage` — nav bar, profile link, vocab link, responsive grid

**Files:**
- Modify: `frontend/src/pages/TopicsPage.tsx`

- [ ] **Step 1: Replace `TopicsPage.tsx`**

Replace the full content of `frontend/src/pages/TopicsPage.tsx`:

```typescript
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { topicsApi, conversationsApi } from "../api/endpoints"
import type { Topic, Conversation } from "../api/endpoints"
import ConversationList from "../components/ConversationList"
import { useAuth } from "../hooks/useAuth"

function getInitials(email: string): string {
  return email.split("@")[0].slice(0, 2).toUpperCase()
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const { logout } = useAuth()
  const navigate = useNavigate()
  const email = (() => {
    try {
      const token = localStorage.getItem("token")
      if (!token) return ""
      const payload = JSON.parse(atob(token.split(".")[1]))
      return payload.email ?? ""
    } catch { return "" }
  })()

  useEffect(() => {
    topicsApi.list().then(r => setTopics(r.data))
    conversationsApi.list().then(r => setConversations(r.data))
  }, [])

  const startChat = async (topicId: string) => {
    const resp = await conversationsApi.create(topicId)
    navigate(`/chat/${resp.data.id}`)
  }

  const deleteConversation = async (id: string) => {
    await conversationsApi.delete(id)
    setConversations(prev => prev.filter(c => c.id !== id))
  }

  const topicNames = Object.fromEntries(topics.map(t => [t.id, t.name]))

  return (
    <div className="min-h-dvh bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3 flex items-center justify-between max-w-2xl mx-auto">
        <h1 className="text-lg font-bold">Topics</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/vocabulary")}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Vocabulary
          </button>
          <button
            onClick={() => navigate("/profile")}
            className="w-8 h-8 rounded-full bg-blue-500 text-white text-xs font-bold flex items-center justify-center hover:opacity-80"
            title={email}
          >
            {email ? getInitials(email) : "?"}
          </button>
          <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">
            Logout
          </button>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-8">
        {/* Topics grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {topics.map(t => (
            <div key={t.id} className="bg-white border rounded-xl p-4 space-y-2 hover:shadow-md transition active:scale-95">
              <button onClick={() => startChat(t.id)} className="w-full text-left">
                <h2 className="font-semibold">{t.name}</h2>
                {t.description && <p className="text-gray-500 text-sm mt-1">{t.description}</p>}
              </button>
              <button
                onClick={() => navigate(`/topics/${t.id}/vocabulary`)}
                className="text-xs text-blue-500 hover:underline"
              >
                Vocabulary →
              </button>
            </div>
          ))}
        </div>

        {/* Conversations */}
        <div>
          <h2 className="text-base font-semibold mb-3">Your Conversations</h2>
          <ConversationList
            conversations={conversations}
            topicNames={topicNames}
            onDelete={deleteConversation}
            onOpen={id => navigate(`/chat/${id}`)}
          />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/TopicsPage.tsx
git commit -m "feat: add profile/vocabulary nav links and responsive grid to TopicsPage"
```

---

## Task 10: Update `MessageInput` — sticky voice reply default

**Files:**
- Modify: `frontend/src/components/MessageInput.tsx`

- [ ] **Step 1: Replace `MessageInput.tsx`**

Replace the full content of `frontend/src/components/MessageInput.tsx`:

```typescript
import { useState, useRef } from "react"

interface Props {
  onSendText: (text: string, replyWithVoice: boolean) => void
  onSendVoice: (blob: Blob, replyWithVoice: boolean) => void
  disabled: boolean
}

const STORAGE_KEY = "replyWithVoice"

function getStoredVoicePref(): boolean {
  try {
    const val = localStorage.getItem(STORAGE_KEY)
    return val === null ? true : val === "true"
  } catch {
    return true
  }
}

export default function MessageInput({ onSendText, onSendVoice, disabled }: Props) {
  const [text, setText] = useState("")
  const [replyWithVoice, setReplyWithVoice] = useState(getStoredVoicePref)
  const [recording, setRecording] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const toggleVoicePref = () => {
    setReplyWithVoice(prev => {
      const next = !prev
      try { localStorage.setItem(STORAGE_KEY, String(next)) } catch {}
      return next
    })
  }

  const handleSend = () => {
    if (!text.trim()) return
    onSendText(text.trim(), replyWithVoice)
    setText("")
  }

  const toggleRecording = async () => {
    if (recording) {
      mediaRef.current?.stop()
      setRecording(false)
    } else {
      setMicError(null)
      try {
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
      } catch {
        setMicError("Microphone access denied. Please allow microphone access and try again.")
      }
    }
  }

  return (
    <div className="border-t bg-white safe-bottom">
      {micError && <div className="text-red-500 text-xs px-4 pt-2">{micError}</div>}
      <div className="flex items-center gap-2 px-3 py-3">
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Type a message..."
          disabled={disabled || recording}
          className="flex-1 min-w-0 border rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={disabled || recording || !text.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-full text-sm hover:bg-blue-700 disabled:opacity-50 shrink-0"
        >
          Send
        </button>
        <button
          onClick={toggleRecording}
          disabled={disabled}
          className={`px-3 py-2 rounded-full text-sm shrink-0 ${recording ? "bg-red-500 text-white animate-pulse" : "bg-gray-200 text-gray-700"} hover:opacity-80 disabled:opacity-50`}
        >
          {recording ? "■" : "🎤"}
        </button>
        <button
          onClick={toggleVoicePref}
          title={replyWithVoice ? "Voice reply on" : "Voice reply off"}
          className={`px-3 py-2 rounded-full text-sm shrink-0 ${replyWithVoice ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"} hover:opacity-80`}
        >
          🔊
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageInput.tsx
git commit -m "feat: sticky voice reply default (localStorage, default true)"
```

---

## Task 11: Update `MessageBubble` — hide/show text toggle

**Files:**
- Modify: `frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Replace `MessageBubble.tsx`**

Replace the full content of `frontend/src/components/MessageBubble.tsx`:

```typescript
import { useState } from "react"
import type { ChatMessage } from "../hooks/useChat"

function highlightVocab(content: string, activeVocab: string[]): React.ReactNode {
  if (!activeVocab.length) return content

  const pattern = new RegExp(
    `(${activeVocab.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join("|")})`,
    "gi"
  )
  const parts = content.split(pattern)

  return parts.map((part, i) => {
    const isMatch = activeVocab.some(w => w.toLowerCase() === part.toLowerCase())
    return isMatch
      ? <mark key={i} className="bg-yellow-200 rounded px-0.5">{part}</mark>
      : part
  })
}

export default function MessageBubble({
  message,
  activeVocab = [],
}: {
  message: ChatMessage
  activeVocab?: string[]
}) {
  const isUser = message.role === "user"
  const [textHidden, setTextHidden] = useState(false)

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-1`}>
      <div className={`max-w-[85%] sm:max-w-md px-4 py-2 rounded-2xl ${
        isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800 shadow-sm"
      }`}>
        {!textHidden && (
          <p className="text-sm leading-relaxed">
            {isUser ? message.content : highlightVocab(message.content, activeVocab)}
          </p>
        )}
        {message.audio_url && (
          <div className="mt-2 flex items-center gap-2">
            <audio controls src={message.audio_url} className="w-full h-8" />
            {!isUser && (
              <button
                onClick={() => setTextHidden(h => !h)}
                className="text-gray-400 hover:text-gray-600 text-xs shrink-0"
                title={textHidden ? "Show text" : "Hide text"}
              >
                {textHidden ? "👁" : "🙈"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageBubble.tsx
git commit -m "feat: add hide/show text toggle to assistant message bubbles"
```

---

## Task 12: Update `useChat` — expose `topicName`, auto-play audio

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Replace `useChat.ts`**

Replace the full content of `frontend/src/hooks/useChat.ts`:

```typescript
import { useState, useCallback, useEffect, useRef } from "react"
import { chatApi, conversationsApi } from "../api/endpoints"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeVocab, setActiveVocab] = useState<string[]>([])
  const [topicName, setTopicName] = useState<string>("")
  const lastAudioUrlRef = useRef<string | null>(null)

  // Load history and topic name on mount
  useEffect(() => {
    let cancelled = false

    async function loadHistory() {
      try {
        const res = await chatApi.history(conversationId)
        if (!cancelled) {
          setMessages(res.data.messages.map(m => ({
            role: m.role,
            content: m.content,
            audio_url: m.audio_url,
          })))
        }
      } catch {
        // Silently ignore — empty chat is fine
      }
    }

    async function loadTopicName() {
      try {
        const res = await conversationsApi.list()
        const conv = res.data.find(c => c.id === conversationId)
        if (conv && !cancelled) setTopicName(conv.topic_name)
      } catch {
        // Not critical
      }
    }

    loadHistory()
    loadTopicName()
    return () => { cancelled = true }
  }, [conversationId])

  // Auto-play latest assistant audio
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (
      last &&
      last.role === "assistant" &&
      last.audio_url &&
      last.audio_url !== lastAudioUrlRef.current
    ) {
      lastAudioUrlRef.current = last.audio_url
      const audio = new Audio(last.audio_url)
      audio.play().catch(() => {
        // Auto-play blocked by browser — user will need to tap play manually
      })
    }
  }, [messages])

  const sendText = useCallback(async (content: string, replyWithVoice: boolean) => {
    setError(null)
    setMessages(prev => [...prev, { role: "user", content }])
    setLoading(true)
    try {
      const res = await chatApi.sendText(conversationId, content, replyWithVoice)
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  const sendVoice = useCallback(async (audioBlob: Blob, replyWithVoice: boolean) => {
    setError(null)
    setLoading(true)
    try {
      const res = await chatApi.sendAudio(conversationId, audioBlob, replyWithVoice)
      const { user_message, assistant_message, active_vocab } = res.data
      if (active_vocab?.length) setActiveVocab(active_vocab)
      setMessages(prev => [
        ...prev,
        { role: "user", content: user_message.content, audio_url: user_message.audio_url },
        { role: "assistant", content: assistant_message.content, audio_url: assistant_message.audio_url },
      ])
    } catch {
      setError("Failed to get a response. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  return { messages, loading, error, sendText, sendVoice, activeVocab, topicName }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: auto-play assistant audio and expose topicName in useChat"
```

---

## Task 13: Update `ChatPage` — topic name header, responsive layout

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: Replace `ChatPage.tsx`**

Replace the full content of `frontend/src/pages/ChatPage.tsx`:

```typescript
import { useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, loading, error, sendText, sendVoice, activeVocab, topicName } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  return (
    <div className="flex flex-col h-dvh bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white border-b shrink-0">
        <button
          onClick={() => navigate("/topics")}
          className="text-blue-600 text-sm hover:underline shrink-0"
        >
          ←
        </button>
        <div className="min-w-0">
          <p className="text-sm font-semibold truncate">{topicName || "Chat"}</p>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2 shrink-0">{error}</div>}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-2 py-4">
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            message={m}
            activeVocab={m.role === "assistant" ? activeVocab : []}
          />
        ))}
        {loading && (
          <div className="flex justify-start mb-2 px-1">
            <div className="bg-white border rounded-2xl px-4 py-3 text-sm text-gray-500 flex items-center gap-1 shadow-sm">
              <span className="animate-bounce [animation-delay:0ms]">●</span>
              <span className="animate-bounce [animation-delay:150ms]">●</span>
              <span className="animate-bounce [animation-delay:300ms]">●</span>
              <span className="ml-2 text-xs">Thinking…</span>
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

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ChatPage.tsx
git commit -m "feat: show topic name in chat header and use h-dvh for mobile"
```

---

## Task 14: Responsive pass — VocabularyPage (per-topic)

**Files:**
- Modify: `frontend/src/pages/VocabularyPage.tsx`

- [ ] **Step 1: Update outer container and table to be mobile-friendly**

In `frontend/src/pages/VocabularyPage.tsx`, replace the outer `div` className from:
```
"min-h-screen bg-gray-50 p-8 max-w-2xl mx-auto space-y-6"
```
to:
```
"min-h-dvh bg-gray-50 px-4 py-6 max-w-2xl mx-auto space-y-6"
```

Replace the `<table>` block (lines 83–124) with a card-list layout that works on mobile:

```typescript
      {/* Mobile card list */}
      <div className="space-y-2 sm:hidden">
        {words.map(item => (
          <div key={item.id} className="bg-white border rounded-xl px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{item.word}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {new Date(item.added_at).toLocaleDateString()} · {item.usage_count} uses
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => handleToggleActive(item)}
                className={`px-2 py-1 rounded-full text-xs ${item.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
              >
                {item.is_active ? "Active" : "Off"}
              </button>
              <button onClick={() => handleDelete(item.id)} className="text-red-400 hover:text-red-600 text-xs">✕</button>
            </div>
          </div>
        ))}
        {words.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-8">No words yet. Add your first word above.</p>
        )}
      </div>

      {/* Desktop table */}
      <table className="hidden sm:table w-full bg-white border rounded-lg text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="px-4 py-2">Word</th>
            <th className="px-4 py-2">Added</th>
            <th className="px-4 py-2">Times Used</th>
            <th className="px-4 py-2">Active</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {words.map(item => (
            <tr key={item.id} className="border-b last:border-0">
              <td className="px-4 py-2 font-medium">{item.word}</td>
              <td className="px-4 py-2 text-gray-500">{new Date(item.added_at).toLocaleDateString()}</td>
              <td className="px-4 py-2 text-gray-500">{item.usage_count}</td>
              <td className="px-4 py-2">
                <button
                  onClick={() => handleToggleActive(item)}
                  className={`px-2 py-1 rounded text-xs ${item.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                >
                  {item.is_active ? "Active" : "Inactive"}
                </button>
              </td>
              <td className="px-4 py-2">
                <button onClick={() => handleDelete(item.id)} className="text-red-400 hover:text-red-600 text-xs">Delete</button>
              </td>
            </tr>
          ))}
          {words.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-6 text-center text-gray-400">No words yet. Add your first word above.</td>
            </tr>
          )}
        </tbody>
      </table>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/VocabularyPage.tsx
git commit -m "feat: mobile-first layout for per-topic VocabularyPage"
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ User profile page (email, level, total messages, avatar with fallback)
- ✅ Global vocabulary page (read-only, all topics grouped)
- ✅ Chat auto-play audio
- ✅ Hide/show text toggle in chat
- ✅ Topic name in chat header
- ✅ Voice reply sticky default (localStorage, default true)
- ✅ Mobile-first responsive (h-dvh, grid-cols-1, card lists, max-w containers)

**Type consistency check:**
- `UserProfile` defined in Task 5, used in Tasks 6 ✅
- `VocabularyItemWithTopic` defined in Task 5, used in Task 7 ✅
- `topicName` returned from `useChat` in Task 12, consumed in Task 13 ✅
- `Conversation.topic_name` added to type in Task 5, populated by backend in Task 3, consumed in Task 12 ✅
- `authApi.me()` added in Task 5, used in Task 6 ✅
- `vocabularyApi.listAll()` added in Task 5, used in Task 7 ✅
