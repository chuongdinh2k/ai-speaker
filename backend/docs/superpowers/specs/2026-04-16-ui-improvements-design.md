# UI Improvements Design

**Date:** 2026-04-16  
**Status:** Approved

## Summary

Five UI improvements to the AI Speaker app:
1. User profile page (email, level, message count, avatar)
2. Global vocabulary tracking page (read-only, all topics)
3. Chat: auto-play reply audio + hide/show text toggle + topic name in header
4. Voice reply defaults to `true` and is sticky (localStorage)
5. Mobile-first responsive overhaul

---

## Section 1 — Backend Changes

### 1a. Avatar URL

- New Alembic migration: add `avatar_url: str | None` column to `users` table
- Update `UserResponse` schema to include `avatar_url: str | None`
- `/auth/me` endpoint already exists — update it to return `avatar_url` and `level`

### 1b. Message Count on `/auth/me`

- Add `total_messages: int` to `UserResponse`
- Computed in the `/auth/me` handler by counting `messages` rows where `role = "user"` joined through `conversations` for the current user

### 1c. Global Vocabulary Endpoint

- New: `GET /vocabularies/all` — returns all vocab for the current user across all topics
- Each item includes `topic_name: str` (joined from `topics` table)
- Reuses existing `VocabularyItem` schema shape, extended with `topic_name`

---

## Section 2 — Frontend: New Pages & Routes

### 2a. User Profile Page (`/profile`)

- Route: `/profile` (private)
- Entry point: avatar/initials button added to TopicsPage and ChatPage headers
- Displays:
  - Avatar: `avatar_url` if set, else colored circle with email initials
  - Email
  - CEFR level badge (e.g. "A2", "B1")
  - Total messages sent
- Read-only (upload avatar deferred to future task)
- Layout: centered card, full-width on mobile

### 2b. Global Vocabulary Page (`/vocabulary`)

- Route: `/vocabulary` (private)
- Linked from TopicsPage header nav
- Shows all user vocabulary grouped by topic name
- Fields shown: Word, Topic, Added date, Times Used, Active status
- Read-only (no add/delete on this page)
- Mobile layout: card-style rows (not a table)

### 2c. Chat Page Improvements

- **Topic name in header:** fetch topic name via conversation data (conversations list already returns `topic_id`; join topic name client-side from a topics fetch or extend conversation API to return `topic_name`)
- **Auto-play audio:** `useEffect` in `useChat` hook watches for new assistant messages with `audio_url`; plays via `new Audio(url).play()`
- **Hide/show text toggle:** per-message local state in `MessageBubble`; eye icon button on assistant messages; text hidden = show only audio player
- **Voice reply sticky default:** replace checkbox with a toggle; read/write `localStorage` key `"replyWithVoice"`; default `true` on first load

### 2d. Responsive Overhaul (Mobile-First)

- All pages: `max-w-2xl mx-auto px-4` container, safe padding on small screens
- TopicsPage topic grid: `grid-cols-1 sm:grid-cols-2`
- ChatPage: full viewport height with `h-dvh` (dynamic viewport height for mobile browsers)
- MessageBubble: `max-w-[85%]` on mobile instead of fixed `max-w-xs`
- Vocabulary table: convert to card list on mobile (`sm:table` hidden on small screens)

---

## Section 3 — Data Flow & API Types

### Updated Types

```typescript
// UserResponse (new fields)
interface UserProfile {
  id: string
  email: string
  role: string
  level: string
  avatar_url: string | null
  total_messages: number
}

// VocabularyItem (extended for global endpoint)
interface VocabularyItemWithTopic extends VocabularyItem {
  topic_name: string
}

// Conversation (extend to carry topic_name for chat header)
interface Conversation {
  id: string
  topic_id: string
  topic_name: string   // added via server-side join
  created_at: string
}
```

### New API Calls

- `authApi.me()` — `GET /auth/me` — returns `UserProfile`
- `vocabularyApi.listAll()` — `GET /vocabularies/all` — returns `VocabularyItemWithTopic[]`

### State Management

- **User profile:** fetched on `/profile` mount, local state only (no global store)
- **Auto-play:** `useEffect` in `useChat` detects new assistant message with `audio_url`, calls `new Audio(url).play()`
- **Voice reply preference:** `localStorage` key `"replyWithVoice"`, default `true`, read on `MessageInput` mount
- **Text hide/show:** `useState<boolean>` inside each `MessageBubble`, default `false` (text visible)

---

## Implementation Order

1. Alembic migration for `avatar_url`
2. Update `/auth/me` schema + handler (add `avatar_url`, `level`, `total_messages`)
3. Add `GET /vocabularies/all` endpoint
4. Extend conversations list to return `topic_name`
5. Add `authApi.me()` and `vocabularyApi.listAll()` to frontend endpoints
6. Build `ProfilePage`
7. Build `GlobalVocabularyPage`
8. Update `ChatPage` (topic name header, audio auto-play, hide/show text, sticky voice toggle)
9. Update `MessageInput` (sticky voice reply)
10. Responsive pass across all pages
