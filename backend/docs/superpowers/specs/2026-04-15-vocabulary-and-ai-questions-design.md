# Vocabulary System & AI Question Prompting — Design Spec

**Date:** 2026-04-15  
**Status:** Approved

---

## Overview

Two related features:

1. **AI always asks questions** — the chatbot ends every response with a question to engage the user, unless the user's last message was already a question. If the user gave a very short/quiet answer, the AI draws them out with a question.
2. **Vocabulary system** — users build a personal vocabulary list per topic, select up to 5 "active" words as their current study set, and the AI naturally uses and asks about those words during conversation. Active vocab words are highlighted in the chat UI.

---

## Data Model

### New table: `user_vocabularies`

```sql
CREATE TABLE user_vocabularies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    topic_id    UUID NOT NULL REFERENCES topics(id),
    word        TEXT NOT NULL,
    added_at    TIMESTAMP WITH TIME ZONE DEFAULT now(),
    usage_count INT NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX ON user_vocabularies (user_id, topic_id);
```

- `is_active=true` = word is in the user's active study set for that topic (max 5 per user+topic enforced in application layer)
- `usage_count` increments each time the word appears in the assistant's reply (simple string match, case-insensitive)
- No expiry — user manages their active set manually

---

## Backend

### New SQLAlchemy model: `UserVocabulary`

File: `app/models/vocabulary.py`

### New API endpoints: `/vocabularies`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/vocabularies?topic_id=<id>` | List all words for current user + topic |
| POST | `/vocabularies` | Add a word `{ topic_id, word }` |
| DELETE | `/vocabularies/{id}` | Remove a word |
| PATCH | `/vocabularies/{id}/activate` | Set `is_active=true` (enforces max 5) |
| PATCH | `/vocabularies/{id}/deactivate` | Set `is_active=false` |

All endpoints require authenticated user. `activate` returns 400 if user already has 5 active words for that topic.

Files: `app/vocabularies/router.py`, `app/vocabularies/service.py`, `app/schemas/vocabulary.py`

### Redis caching

Three Redis keys per user+topic:

| Key | Value | TTL | Invalidated on |
|-----|-------|-----|----------------|
| `active_vocab:{user_id}:{topic_id}` | JSON array of active word strings | 24h | activate / deactivate |
| `vocab_history:{user_id}:{topic_id}` | JSON array of latest 10 words (by added_at) | 1h | new word added / word deleted |
| `system_prompt_vocab:{user_id}:{topic_id}` | Fully built system prompt string (base + vocab injection) | 24h | activate / deactivate |

- All three keys use DB fallback on cache miss and are repopulated after the fallback read.
- `system_prompt_vocab` is invalidated (deleted) on every activate/deactivate so the next chat request rebuilds it fresh with the updated word list.
- Redis unavailability degrades gracefully — all values fall back to DB reads.

### Chat pipeline changes (`app/chat/rag.py`)

`get_system_prompt` is extended (or a new `get_vocab_context` helper added) to:

1. Check `system_prompt_vocab:{user_id}:{topic_id}` in Redis — if hit, return immediately (no DB or string building needed)
2. On miss: read base system prompt from DB, read active vocab from `active_vocab:{user_id}:{topic_id}` (Redis → DB fallback), read vocab history from `vocab_history:{user_id}:{topic_id}` (Redis → DB fallback)
3. Build the full prompt and cache it at `system_prompt_vocab:{user_id}:{topic_id}` with 24h TTL
4. The built prompt appends to the base system prompt:

```
Active vocabulary to focus on: [word1, word2, ...]
Recent vocabulary history: [word3, word4, ...]

Always end your response with a question to the user based on the conversation context.
Exception: if the user's last message was already a question, you do not need to ask one back.
If the user gave a very short or one-word answer, ask something to draw them out.
```

### Usage count increment (`app/chat/service.py`)

After the LLM returns `reply_text`:
- Load active vocab for user+topic from Redis
- For each active word, check if it appears in `reply_text` (case-insensitive)
- Bulk-increment `usage_count` in DB for matched words
- This is fire-and-forget (non-blocking, wrapped in try/except)

### Chat response payload change

The `handle_chat_message` return dict gains one new field:
```python
"active_vocab": ["word1", "word2", ...]  # list of active words for this topic
```

This is sourced from Redis (already in memory at response time — no extra query).

The `user_id` must be passed into `handle_chat_message` to support vocab lookup. The conversation's `topic_id` is resolved from DB (already available via the existing system prompt query).

---

## Frontend

### New page: `VocabularyPage` (`/topics/:topicId/vocabulary`)

Route: `/topics/:topicId/vocabulary`

UI elements:
- Text input + "Add word" button
- Table with columns: **Word | Added Date | Times Used | Active**
  - Active column: toggle button (activate/deactivate), enforces max 5 with inline error message
  - Delete button per row
- On activate, if already 5 active: show inline error "You already have 5 active words. Deactivate one first."

File: `frontend/src/pages/VocabularyPage.tsx`

### TopicsPage update

Add a "Vocabulary" link button next to each topic card, navigating to `/topics/:topicId/vocabulary`.

### ChatPage — vocabulary highlighting

- On chat page mount, fetch active vocab from `/vocabularies?topic_id=<id>` OR read from the chat response payload's `active_vocab` field (preferred — no extra call)
- Store active vocab in local state
- In `MessageBubble`, for assistant messages: scan the content for active vocab words (case-insensitive) and wrap matches in a `<mark>` or styled `<span>` for highlight

File changes: `frontend/src/pages/ChatPage.tsx`, `frontend/src/components/MessageBubble.tsx`

---

## New API module structure

```
backend/app/
  vocabularies/
    __init__.py
    router.py
    service.py
  models/
    vocabulary.py          (new)
  schemas/
    vocabulary.py          (new)
```

Registered in `app/main.py`.

---

## Alembic migration

One new migration: create `user_vocabularies` table with index on `(user_id, topic_id)`.

---

## Error handling

- Max 5 active words: enforced in service layer, returns HTTP 400
- Redis unavailable: fall back to DB for vocab reads; activate/deactivate still writes to DB, Redis update is best-effort
- `usage_count` increment failure: logged as warning, does not affect chat response

---

## Out of scope

- Vocabulary word validation (no dictionary API check — user trusts themselves)
- Daily reset or expiry of active words
- Admin-managed shared vocabulary lists
- Vocabulary search or filtering
