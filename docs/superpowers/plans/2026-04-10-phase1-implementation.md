# Phase 1: AI Speaker Chat App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where users log in, pick a topic, and chat with an AI bot that responds in text or voice, with RAG-based conversation history.

**Architecture:** Single FastAPI monolith with 4 internal modules (auth, topics, chat, voice). React + Tailwind frontend. Postgres + pgvector for storage and semantic search. Redis for caching. Non-streaming WebSocket chat.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic, LangChain, OpenAI SDK, pgvector, Redis (redis-py), React 18, Tailwind CSS, Vite, Docker Compose

---

## File Structure

### Backend (`backend/`)

```
backend/
├── app/
│   ├── main.py                   # FastAPI app factory, router registration
│   ├── config.py                 # Settings from env vars (pydantic-settings)
│   ├── database.py               # SQLAlchemy engine, session factory
│   ├── redis_client.py           # Redis connection singleton
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py               # User ORM model
│   │   ├── topic.py              # Topic ORM model
│   │   ├── conversation.py       # Conversation ORM model
│   │   ├── message.py            # Message ORM model (with pgvector column)
│   │   ├── prompt_template.py    # PromptTemplate ORM model
│   │   └── subscription.py       # Subscription ORM model (stub)
│   ├── schemas/
│   │   ├── auth.py               # Pydantic request/response schemas for auth
│   │   ├── topic.py              # Pydantic schemas for topics
│   │   ├── conversation.py       # Pydantic schemas for conversations
│   │   └── chat.py               # Pydantic schemas for WS messages
│   ├── auth/
│   │   ├── router.py             # /auth/* endpoints
│   │   ├── service.py            # register, login logic
│   │   └── dependencies.py       # get_current_user, require_admin JWT deps
│   ├── topics/
│   │   ├── router.py             # /topics/* endpoints
│   │   └── service.py            # topic CRUD
│   ├── conversations/
│   │   ├── router.py             # /conversations/* endpoints
│   │   └── service.py            # upsert, list, soft-delete
│   ├── chat/
│   │   ├── router.py             # WebSocket /ws/chat/{conversation_id}
│   │   ├── service.py            # orchestrates RAG pipeline
│   │   └── rag.py                # embed, retrieve, build prompt
│   ├── voice/
│   │   ├── router.py             # /voice/transcribe endpoint
│   │   └── service.py            # Whisper STT, OpenAI TTS
│   └── admin/
│       └── router.py             # /admin/* endpoints
├── alembic/
│   ├── env.py
│   └── versions/                 # migration files
├── tests/
│   ├── conftest.py               # pytest fixtures: test DB, test client
│   ├── test_auth.py
│   ├── test_topics.py
│   ├── test_conversations.py
│   ├── test_chat.py
│   └── test_voice.py
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                   # routes
│   ├── api/
│   │   ├── client.ts             # axios instance with JWT interceptor
│   │   └── endpoints.ts          # typed API call functions
│   ├── hooks/
│   │   ├── useAuth.ts            # login, register, logout, JWT storage
│   │   └── useChat.ts            # WebSocket connection, send/receive
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── TopicsPage.tsx        # pick a topic
│   │   └── ChatPage.tsx          # chat UI
│   └── components/
│       ├── MessageBubble.tsx     # single message (text + optional audio player)
│       ├── MessageInput.tsx      # text input + voice record button
│       └── ConversationList.tsx  # sidebar list with delete
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── Dockerfile
```

### Root

```
docker-compose.yml
.env.example
```

---

## Task 1: Project Scaffold & Config

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pgvector==0.2.5
redis==5.0.4
pydantic-settings==2.2.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
openai==1.30.1
langchain==0.2.1
langchain-openai==0.1.8
python-multipart==0.0.9
aiofiles==23.2.1
pytest==8.2.0
pytest-asyncio==0.23.7
httpx==0.27.0
```

- [ ] **Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    openai_api_key: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    audio_storage_path: str = "/app/audio"
    rag_top_k: int = 5
    rag_recent_window: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 3: Create `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aispeaker
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
JWT_SECRET=change-me-in-production
AUDIO_STORAGE_PATH=/app/audio
```

- [ ] **Step 4: Create `backend/app/main.py`**

```python
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
```

- [ ] **Step 5: Install deps and verify app starts**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in real values
uvicorn app.main:app --reload
```

Expected: server starts on http://localhost:8000, `/health` returns `{"status": "ok"}`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/main.py backend/.env.example
git commit -m "feat: backend scaffold with config and health endpoint"
```

---

## Task 2: Database Models & Migrations

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/topic.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/prompt_template.py`
- Create: `backend/app/models/subscription.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Create `backend/app/models/user.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 3: Create `backend/app/models/topic.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Create `backend/app/models/conversation.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_user_topic"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    topic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 5: Create `backend/app/models/message.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 6: Create `backend/app/models/prompt_template.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: Create `backend/app/models/subscription.py`**

```python
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free")
    status: Mapped[str] = mapped_column(String, default="active")
```

- [ ] **Step 8: Create `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.topic import Topic
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.prompt_template import PromptTemplate
from app.models.subscription import Subscription

__all__ = ["User", "Topic", "Conversation", "Message", "PromptTemplate", "Subscription"]
```

- [ ] **Step 9: Init Alembic and create initial migration**

```bash
cd backend
alembic init alembic
```

Edit `backend/alembic/env.py` — replace the `target_metadata = None` line and add async support:

```python
# at the top, add:
from app.database import Base
from app.models import *  # noqa: F401, F403 — registers all models
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config

# replace target_metadata line:
target_metadata = Base.metadata

# replace run_migrations_online() with:
def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(do_run())

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

Edit `backend/alembic.ini` — set the sqlalchemy.url:
```
sqlalchemy.url = postgresql+asyncpg://user:password@localhost:5432/aispeaker
```

Then generate the migration:
```bash
alembic revision --autogenerate -m "initial schema"
```

- [ ] **Step 10: Manually add pgvector extension to migration**

Open the generated migration file in `alembic/versions/`. At the top of `upgrade()`, add:

```python
from alembic import op

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ... rest of generated upgrade code
```

- [ ] **Step 11: Run migration**

```bash
alembic upgrade head
```

Expected: tables created in Postgres without errors.

- [ ] **Step 12: Commit**

```bash
git add backend/app/database.py backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat: database models and initial migration"
```

---

## Task 3: Auth Module

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Create `backend/app/schemas/auth.py`**

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
```

- [ ] **Step 2: Create `backend/app/auth/service.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.models.user import User
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def register_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ValueError("Email already registered")
    user = User(email=email, password_hash=pwd_context.hash(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise ValueError("Invalid credentials")
    return user

def create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user.id), "email": user.email, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
```

- [ ] **Step 3: Create `backend/app/auth/dependencies.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings

bearer = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
```

- [ ] **Step 4: Create `backend/app/auth/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.auth.service import register_user, authenticate_user, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse(id=str(user.id), email=user.email, role=user.role)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    token = create_access_token(user)
    return TokenResponse(access_token=token)

@router.post("/logout")
async def logout():
    # JWT is stateless; client drops the token
    return {"message": "logged out"}

@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    return UserResponse(id=user["sub"], email=user["email"], role=user["role"])
```

- [ ] **Step 5: Register auth router in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/tests/conftest.py`**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.config import settings

TEST_DB_URL = settings.database_url.replace("/aispeaker", "/aispeaker_test")

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 7: Write failing tests in `backend/tests/test_auth.py`**

```python
import pytest

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={"email": "a@test.com", "password": "pass123"})
    assert resp.status_code == 201
    assert resp.json()["email"] == "a@test.com"
    assert resp.json()["role"] == "user"

@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    resp = await client.post("/auth/register", json={"email": "dup@test.com", "password": "pass123"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={"email": "b@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "b@test.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "c@test.com", "password": "pass123"})
    resp = await client.post("/auth/login", json={"email": "c@test.com", "password": "wrong"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_me_returns_user(client):
    await client.post("/auth/register", json={"email": "d@test.com", "password": "pass123"})
    login = await client.post("/auth/login", json={"email": "d@test.com", "password": "pass123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "d@test.com"
```

- [ ] **Step 8: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_auth.py -v
```

Expected: FAIL (module not found or similar — implementation not wired up yet)

- [ ] **Step 9: Run tests again after implementation is wired**

```bash
pytest tests/test_auth.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/ backend/app/auth/ backend/app/main.py backend/tests/
git commit -m "feat: auth module — register, login, JWT"
```

---

## Task 4: Topics Module

**Files:**
- Create: `backend/app/schemas/topic.py`
- Create: `backend/app/topics/service.py`
- Create: `backend/app/topics/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_topics.py`

- [ ] **Step 1: Create `backend/app/schemas/topic.py`**

```python
from pydantic import BaseModel
from uuid import UUID

class TopicCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str | None = None

class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None

class TopicResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    system_prompt: str | None

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Create `backend/app/topics/service.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.topic import Topic

async def list_topics(db: AsyncSession) -> list[Topic]:
    result = await db.execute(select(Topic))
    return result.scalars().all()

async def create_topic(db: AsyncSession, name: str, description: str | None, system_prompt: str | None) -> Topic:
    topic = Topic(name=name, description=description, system_prompt=system_prompt)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

async def update_topic(db: AsyncSession, topic_id: str, name: str | None, description: str | None, system_prompt: str | None) -> Topic:
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise ValueError("Topic not found")
    if name is not None:
        topic.name = name
    if description is not None:
        topic.description = description
    if system_prompt is not None:
        topic.system_prompt = system_prompt
    await db.commit()
    await db.refresh(topic)
    return topic
```

- [ ] **Step 3: Create `backend/app/topics/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.topic import TopicCreate, TopicUpdate, TopicResponse
from app.topics.service import list_topics, create_topic, update_topic
from app.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("", response_model=list[TopicResponse])
async def get_topics(db: AsyncSession = Depends(get_db), _: dict = Depends(get_current_user)):
    return await list_topics(db)

@router.post("", response_model=TopicResponse, status_code=201)
async def post_topic(body: TopicCreate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    return await create_topic(db, body.name, body.description, body.system_prompt)

@router.put("/{topic_id}", response_model=TopicResponse)
async def put_topic(topic_id: str, body: TopicUpdate, db: AsyncSession = Depends(get_db), _: dict = Depends(require_admin)):
    try:
        return await update_topic(db, topic_id, body.name, body.description, body.system_prompt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 4: Register topics router in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write failing tests in `backend/tests/test_topics.py`**

```python
import pytest

async def get_token(client, email, password="pass123", role="user"):
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]

async def get_admin_token(client):
    # Register then manually promote to admin via DB in conftest, or use a helper
    # For tests, we'll seed an admin user directly
    from app.models.user import User
    from app.auth.service import pwd_context
    # This is done via the db_session fixture in conftest
    return None  # see note below

@pytest.mark.asyncio
async def test_list_topics_requires_auth(client):
    resp = await client.get("/topics")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_list_topics_empty(client):
    token = await get_token(client, "topicuser@test.com")
    resp = await client.get("/topics", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_create_topic_requires_admin(client):
    token = await get_token(client, "notadmin@test.com")
    resp = await client.post("/topics", json={"name": "Python"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_create_and_list_topic(client, db_session):
    # Seed admin user directly
    from app.models.user import User
    from app.auth.service import pwd_context, create_access_token
    admin = User(email="admin@test.com", password_hash=pwd_context.hash("pass123"), role="admin")
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token(admin)

    resp = await client.post("/topics", json={"name": "Python", "description": "Python programming", "system_prompt": "You are a Python expert."},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Python"

    user_token = await get_token(client, "reader@test.com")
    list_resp = await client.get("/topics", headers={"Authorization": f"Bearer {user_token}"})
    assert any(t["name"] == "Python" for t in list_resp.json())
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_topics.py -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/topic.py backend/app/topics/ backend/app/main.py backend/tests/test_topics.py
git commit -m "feat: topics module — list, create, update (admin)"
```

---

## Task 5: Conversations Module

**Files:**
- Create: `backend/app/schemas/conversation.py`
- Create: `backend/app/conversations/service.py`
- Create: `backend/app/conversations/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_conversations.py`

- [ ] **Step 1: Create `backend/app/schemas/conversation.py`**

```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class ConversationCreate(BaseModel):
    topic_id: UUID

class ConversationResponse(BaseModel):
    id: UUID
    topic_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 2: Create `backend/app/conversations/service.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from uuid import UUID
from app.models.conversation import Conversation
from app.models.message import Message

async def upsert_conversation(db: AsyncSession, user_id: UUID, topic_id: UUID) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.topic_id == topic_id,
            Conversation.deleted_at == None,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation
    conversation = Conversation(user_id=user_id, topic_id=topic_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

async def list_conversations(db: AsyncSession, user_id: UUID) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    return result.scalars().all()

async def delete_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at == None,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise ValueError("Conversation not found")
    conversation.deleted_at = datetime.utcnow()
    await db.execute(
        update(Message).where(Message.conversation_id == conversation_id)
    )
    await db.commit()
```

- [ ] **Step 3: Create `backend/app/conversations/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.conversations.service import upsert_conversation, list_conversations, delete_conversation
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("", response_model=list[ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await list_conversations(db, UUID(user["sub"]))

@router.post("", response_model=ConversationResponse, status_code=201)
async def post_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    return await upsert_conversation(db, UUID(user["sub"]), body.topic_id)

@router.delete("/{conversation_id}", status_code=204)
async def del_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        await delete_conversation(db, conversation_id, UUID(user["sub"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

- [ ] **Step 4: Register conversations router in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Write failing tests in `backend/tests/test_conversations.py`**

```python
import pytest
from uuid import uuid4
from app.models.user import User
from app.models.topic import Topic
from app.auth.service import pwd_context, create_access_token

async def seed_user_and_topic(db_session):
    user = User(email=f"u{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name=f"Topic {uuid4()}", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    return user, topic, create_access_token(user)

@pytest.mark.asyncio
async def test_create_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    resp = await client.post("/conversations", json={"topic_id": str(topic.id)},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    assert resp.json()["topic_id"] == str(topic.id)

@pytest.mark.asyncio
async def test_upsert_returns_same_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    r1 = await client.post("/conversations", json={"topic_id": str(topic.id)},
                           headers={"Authorization": f"Bearer {token}"})
    r2 = await client.post("/conversations", json={"topic_id": str(topic.id)},
                           headers={"Authorization": f"Bearer {token}"})
    assert r1.json()["id"] == r2.json()["id"]

@pytest.mark.asyncio
async def test_list_conversations(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    await client.post("/conversations", json={"topic_id": str(topic.id)},
                      headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

@pytest.mark.asyncio
async def test_delete_conversation(client, db_session):
    user, topic, token = await seed_user_and_topic(db_session)
    create = await client.post("/conversations", json={"topic_id": str(topic.id)},
                               headers={"Authorization": f"Bearer {token}"})
    cid = create.json()["id"]
    del_resp = await client.delete(f"/conversations/{cid}", headers={"Authorization": f"Bearer {token}"})
    assert del_resp.status_code == 204
    list_resp = await client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert not any(c["id"] == cid for c in list_resp.json())
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_conversations.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/conversation.py backend/app/conversations/ backend/app/main.py backend/tests/test_conversations.py
git commit -m "feat: conversations module — upsert, list, soft-delete"
```

---

## Task 6: Voice Module (STT + TTS)

**Files:**
- Create: `backend/app/voice/service.py`
- Create: `backend/app/voice/router.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_voice.py`

- [ ] **Step 1: Create `backend/app/voice/service.py`**

```python
import uuid
import os
import base64
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio bytes to Whisper STT, return transcribed text."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            transcript = await client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcript.text
    finally:
        os.unlink(tmp_path)

async def synthesize_speech(text: str) -> str:
    """Generate TTS audio, save to storage, return relative URL path."""
    response = await client.audio.speech.create(model="tts-1", voice="alloy", input=text)
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(settings.audio_storage_path, filename)
    with open(filepath, "wb") as f:
        f.write(response.content)
    return f"/audio/{filename}"
```

- [ ] **Step 2: Create `backend/app/voice/router.py`**

```python
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
```

- [ ] **Step 3: Register voice router in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
from app.voice.router import router as voice_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)
app.include_router(voice_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Write tests in `backend/tests/test_voice.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.models.user import User
from app.auth.service import pwd_context, create_access_token

async def seed_user(db_session):
    user = User(email=f"v{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_access_token(user)

@pytest.mark.asyncio
async def test_transcribe_requires_auth(client):
    resp = await client.post("/voice/transcribe")
    assert resp.status_code == 403

@pytest.mark.asyncio
async def test_transcribe_returns_text(client, db_session):
    token = await seed_user(db_session)
    with patch("app.voice.service.client") as mock_openai:
        mock_openai.audio.transcriptions.create = AsyncMock(
            return_value=MagicMock(text="Hello world")
        )
        import io
        resp = await client.post(
            "/voice/transcribe",
            files={"file": ("audio.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello world"
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_voice.py -v
```

Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/voice/ backend/app/main.py backend/tests/test_voice.py
git commit -m "feat: voice module — Whisper STT, OpenAI TTS"
```

---

## Task 7: RAG Pipeline & Chat Service

**Files:**
- Create: `backend/app/chat/rag.py`
- Create: `backend/app/chat/service.py`
- Create: `backend/app/redis_client.py`

- [ ] **Step 1: Create `backend/app/redis_client.py`**

```python
import redis.asyncio as redis
from app.config import settings

_redis: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis
```

- [ ] **Step 2: Create `backend/app/chat/rag.py`**

```python
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from openai import AsyncOpenAI
from app.models.message import Message
from app.models.topic import Topic
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

async def embed_text(text_content: str) -> list[float]:
    """Embed a string using OpenAI embeddings, return vector."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text_content,
    )
    return response.data[0].embedding

async def retrieve_context(db: AsyncSession, conversation_id: UUID, query_embedding: list[float]) -> list[dict]:
    """Retrieve top-K semantically similar messages from this conversation."""
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    result = await db.execute(
        text("""
            SELECT role, content FROM messages
            WHERE conversation_id = :conv_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :k
        """),
        {"conv_id": str(conversation_id), "embedding": embedding_str, "k": settings.rag_top_k},
    )
    return [{"role": row.role, "content": row.content} for row in result]

async def get_recent_messages(db: AsyncSession, conversation_id: UUID) -> list[dict]:
    """Get last N messages for recency anchor."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(settings.rag_recent_window)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]

async def get_system_prompt(db: AsyncSession, conversation_id: UUID, redis_client) -> str:
    """Get topic system prompt, cached in Redis."""
    cache_key = f"system_prompt:{conversation_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        text("""
            SELECT t.system_prompt FROM topics t
            JOIN conversations c ON c.topic_id = t.id
            WHERE c.id = :conv_id
        """),
        {"conv_id": str(conversation_id)},
    )
    row = result.fetchone()
    prompt = row.system_prompt if row and row.system_prompt else "You are a helpful assistant."
    await redis_client.setex(cache_key, 3600, prompt)
    return prompt

async def build_messages(system_prompt: str, semantic_context: list[dict], recent: list[dict], user_text: str) -> list[dict]:
    """Assemble the messages list for the LLM call."""
    seen = set()
    combined = []
    for msg in semantic_context + recent:
        key = (msg["role"], msg["content"])
        if key not in seen:
            seen.add(key)
            combined.append(msg)
    return [{"role": "system", "content": system_prompt}] + combined + [{"role": "user", "content": user_text}]
```

- [ ] **Step 3: Create `backend/app/chat/service.py`**

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.models.message import Message
from app.chat.rag import embed_text, retrieve_context, get_recent_messages, get_system_prompt, build_messages
from app.voice.service import transcribe_audio, synthesize_speech

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

async def handle_chat_message(
    db: AsyncSession,
    redis_client,
    conversation_id: UUID,
    text_content: str | None,
    audio_bytes: bytes | None,
    reply_with_voice: bool,
) -> dict:
    """
    Full RAG chat pipeline. Returns {"content": str, "audio_url": str | None}.
    Raises Exception on unrecoverable errors.
    """
    # 1. Resolve text
    if audio_bytes:
        text_content = await transcribe_audio(audio_bytes)

    if not text_content:
        raise ValueError("No text content to process")

    # 2. Embed user message
    embedding = await embed_text(text_content)

    # 3. Store user message with embedding
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=text_content,
        embedding=embedding,
    )
    db.add(user_msg)
    await db.commit()

    # 4. Retrieve context
    semantic_ctx = await retrieve_context(db, conversation_id, embedding)
    recent = await get_recent_messages(db, conversation_id)
    system_prompt = await get_system_prompt(db, conversation_id, redis_client)

    # 5. Build prompt and call LLM
    messages = await build_messages(system_prompt, semantic_ctx, recent, text_content)
    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    reply_text = completion.choices[0].message.content

    # 6. Embed and store assistant message
    reply_embedding = await embed_text(reply_text)
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply_text,
        embedding=reply_embedding,
    )
    db.add(assistant_msg)
    await db.commit()

    # 7. TTS if requested
    audio_url = None
    if reply_with_voice:
        try:
            audio_url = await synthesize_speech(reply_text)
        except Exception:
            audio_url = None  # TTS failure: return text only

    return {"content": reply_text, "audio_url": audio_url}
```

- [ ] **Step 4: Write failing tests in `backend/tests/test_chat.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.models.user import User
from app.models.topic import Topic
from app.models.conversation import Conversation
from app.auth.service import pwd_context, create_access_token

async def seed_conversation(db_session):
    user = User(email=f"chat{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name="Test Topic", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    return user, conv, create_access_token(user)

@pytest.mark.asyncio
async def test_rag_build_messages_deduplicates():
    from app.chat.rag import build_messages
    semantic = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    recent = [{"role": "user", "content": "hello"}]  # duplicate
    result = await build_messages("You are helpful.", semantic, recent, "new question")
    contents = [m["content"] for m in result]
    assert contents.count("hello") == 1
    assert result[0]["role"] == "system"
    assert result[-1]["content"] == "new question"

@pytest.mark.asyncio
async def test_handle_chat_message_text(db_session):
    from app.chat.service import handle_chat_message
    user = User(email=f"svc{uuid4()}@test.com", password_hash=pwd_context.hash("pass"), role="user")
    topic = Topic(name="Svc Topic", system_prompt="Be helpful.")
    db_session.add(user)
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(topic)
    conv = Conversation(user_id=user.id, topic_id=topic.id)
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    with patch("app.chat.rag.openai_client") as mock_emb, \
         patch("app.chat.service.openai_client") as mock_llm:
        mock_emb.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        mock_llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[MagicMock(message=MagicMock(content="The answer is 42."))])
        )
        result = await handle_chat_message(db_session, mock_redis, conv.id, "What is the answer?", None, False)

    assert result["content"] == "The answer is 42."
    assert result["audio_url"] is None
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_chat.py -v
```

Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/redis_client.py backend/app/chat/rag.py backend/app/chat/service.py backend/tests/test_chat.py
git commit -m "feat: RAG pipeline — embed, retrieve, build prompt, LLM call"
```

---

## Task 8: Chat WebSocket Router & Admin Endpoint

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/chat/router.py`
- Create: `backend/app/admin/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/schemas/chat.py`**

```python
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
```

- [ ] **Step 2: Create `backend/app/chat/router.py`**

```python
import base64
import json
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from app.config import settings
from app.database import get_db
from app.redis_client import get_redis
from app.chat.service import handle_chat_message

router = APIRouter(tags=["chat"])

@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    # Authenticate
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    redis_client = await get_redis()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "code": "INVALID_JSON", "message": "Invalid JSON"}))
                continue

            msg_type = data.get("type")
            reply_with_voice = data.get("reply_with_voice", False)

            try:
                if msg_type == "text":
                    result = await handle_chat_message(
                        db, redis_client, conversation_id,
                        text_content=data.get("content"),
                        audio_bytes=None,
                        reply_with_voice=reply_with_voice,
                    )
                elif msg_type == "voice":
                    audio_bytes = base64.b64decode(data.get("audio_base64", ""))
                    result = await handle_chat_message(
                        db, redis_client, conversation_id,
                        text_content=None,
                        audio_bytes=audio_bytes,
                        reply_with_voice=reply_with_voice,
                    )
                else:
                    await websocket.send_text(json.dumps({"type": "error", "code": "UNKNOWN_TYPE", "message": "Unknown message type"}))
                    continue

                await websocket.send_text(json.dumps({"type": "message", "content": result["content"], "audio_url": result["audio_url"]}))

            except Exception as e:
                import logging
                logging.exception("Chat error")
                await websocket.send_text(json.dumps({"type": "error", "code": "CHAT_ERROR", "message": "An error occurred. Please try again."}))

    except WebSocketDisconnect:
        pass
```

- [ ] **Step 3: Create `backend/app/admin/router.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.topic import Topic
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

class UpdatePromptRequest(BaseModel):
    system_prompt: str

@router.put("/topics/{topic_id}/prompt")
async def update_topic_prompt(
    topic_id: str,
    body: UpdatePromptRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic.system_prompt = body.system_prompt
    await db.commit()
    return {"id": str(topic.id), "system_prompt": topic.system_prompt}
```

- [ ] **Step 4: Register all routers in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.auth.router import router as auth_router
from app.topics.router import router as topics_router
from app.conversations.router import router as conversations_router
from app.voice.router import router as voice_router
from app.chat.router import router as chat_router
from app.admin.router import router as admin_router
import os

app = FastAPI(title="AI Speaker")

os.makedirs(settings.audio_storage_path, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_storage_path), name="audio")

app.include_router(auth_router)
app.include_router(topics_router)
app.include_router(conversations_router)
app.include_router(voice_router)
app.include_router(chat_router)
app.include_router(admin_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Manually test WebSocket**

Start the backend:
```bash
uvicorn app.main:app --reload
```

Use a WebSocket client (e.g., `websocat` or browser console):
```
ws://localhost:8000/ws/chat/<conversation_id>?token=<jwt>
```

Send: `{"type": "text", "content": "Hello!", "reply_with_voice": false}`
Expected: `{"type": "message", "content": "...", "audio_url": null}`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/chat/router.py backend/app/admin/router.py backend/app/main.py
git commit -m "feat: WebSocket chat endpoint and admin prompt update"
```

---

## Task 9: React Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/endpoints.ts`

- [ ] **Step 1: Scaffold Vite + React + Tailwind**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install axios react-router-dom
```

- [ ] **Step 2: Configure `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 3: Add Tailwind directives to `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Create `frontend/src/api/client.ts`**

```typescript
import axios from "axios"

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default client
```

- [ ] **Step 5: Create `frontend/src/api/endpoints.ts`**

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
  created_at: string
}

export const authApi = {
  register: (email: string, password: string) =>
    client.post("/auth/register", { email, password }),
  login: (email: string, password: string) =>
    client.post<{ access_token: string }>("/auth/login", { email, password }),
  logout: () => client.post("/auth/logout"),
}

export const topicsApi = {
  list: () => client.get<Topic[]>("/topics"),
}

export const conversationsApi = {
  list: () => client.get<Conversation[]>("/conversations"),
  create: (topic_id: string) => client.post<Conversation>("/conversations", { topic_id }),
  delete: (id: string) => client.delete(`/conversations/${id}`),
}
```

- [ ] **Step 6: Create `frontend/src/App.tsx`**

```typescript
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import LoginPage from "./pages/LoginPage"
import TopicsPage from "./pages/TopicsPage"
import ChatPage from "./pages/ChatPage"

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
        <Route path="*" element={<Navigate to="/topics" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 7: Verify frontend starts**

```bash
npm run dev
```

Expected: Vite dev server starts at http://localhost:5173, navigates to `/login`

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: React frontend scaffold with routing and API client"
```

---

## Task 10: Auth Hook & Login Page

**Files:**
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Create `frontend/src/hooks/useAuth.ts`**

```typescript
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { authApi } from "../api/endpoints"

export function useAuth() {
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const login = async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      const resp = await authApi.login(email, password)
      localStorage.setItem("token", resp.data.access_token)
      navigate("/topics")
    } catch {
      setError("Invalid email or password")
    } finally {
      setLoading(false)
    }
  }

  const register = async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      await authApi.register(email, password)
      await login(email, password)
    } catch {
      setError("Registration failed. Email may already be in use.")
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem("token")
    navigate("/login")
  }

  return { login, register, logout, error, loading }
}
```

- [ ] **Step 2: Create `frontend/src/pages/LoginPage.tsx`**

```typescript
import { useState } from "react"
import { useAuth } from "../hooks/useAuth"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isRegister, setIsRegister] = useState(false)
  const { login, register, error, loading } = useAuth()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isRegister) register(email, password)
    else login(email, password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-bold text-center">{isRegister ? "Register" : "Login"}</h1>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <input
          type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <input
          type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <button type="submit" disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "..." : isRegister ? "Register" : "Login"}
        </button>
        <p className="text-center text-sm text-gray-500 cursor-pointer" onClick={() => setIsRegister(!isRegister)}>
          {isRegister ? "Already have an account? Login" : "No account? Register"}
        </p>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Test manually**

Open http://localhost:5173/login, register a new account, verify redirect to `/topics`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useAuth.ts frontend/src/pages/LoginPage.tsx
git commit -m "feat: login/register page with JWT auth"
```

---

## Task 11: Topics Page & Conversation List

**Files:**
- Create: `frontend/src/components/ConversationList.tsx`
- Create: `frontend/src/pages/TopicsPage.tsx`

- [ ] **Step 1: Create `frontend/src/components/ConversationList.tsx`**

```typescript
import { Conversation } from "../api/endpoints"

interface Props {
  conversations: Conversation[]
  topicNames: Record<string, string>
  onDelete: (id: string) => void
  onOpen: (id: string) => void
}

export default function ConversationList({ conversations, topicNames, onDelete, onOpen }: Props) {
  if (conversations.length === 0) return <p className="text-gray-400 text-sm">No conversations yet.</p>
  return (
    <ul className="space-y-2">
      {conversations.map(c => (
        <li key={c.id} className="flex items-center justify-between bg-white border rounded px-4 py-2">
          <button onClick={() => onOpen(c.id)} className="text-blue-600 hover:underline text-sm">
            {topicNames[c.topic_id] ?? "Unknown topic"}
          </button>
          <button onClick={() => onDelete(c.id)} className="text-red-400 hover:text-red-600 text-xs">
            Delete
          </button>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 2: Create `frontend/src/pages/TopicsPage.tsx`**

```typescript
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { topicsApi, conversationsApi, Topic, Conversation } from "../api/endpoints"
import ConversationList from "../components/ConversationList"
import { useAuth } from "../hooks/useAuth"

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const { logout } = useAuth()
  const navigate = useNavigate()

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
    <div className="min-h-screen bg-gray-50 p-8 max-w-2xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Topics</h1>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-700">Logout</button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {topics.map(t => (
          <button key={t.id} onClick={() => startChat(t.id)}
            className="bg-white border rounded-lg p-4 text-left hover:shadow-md transition">
            <h2 className="font-semibold">{t.name}</h2>
            {t.description && <p className="text-gray-500 text-sm mt-1">{t.description}</p>}
          </button>
        ))}
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-3">Your Conversations</h2>
        <ConversationList
          conversations={conversations}
          topicNames={topicNames}
          onDelete={deleteConversation}
          onOpen={id => navigate(`/chat/${id}`)}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Test manually**

Seed a topic via API (or admin endpoint), verify it appears on the topics page, click to create a conversation, verify redirect to `/chat/<id>`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ConversationList.tsx frontend/src/pages/TopicsPage.tsx
git commit -m "feat: topics page with conversation list and delete"
```

---

## Task 12: Chat Page (WebSocket UI)

**Files:**
- Create: `frontend/src/hooks/useChat.ts`
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/components/MessageInput.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 1: Create `frontend/src/hooks/useChat.ts`**

```typescript
import { useEffect, useRef, useState, useCallback } from "react"

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  audio_url?: string | null
}

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("token")
    const wsUrl = `${import.meta.env.VITE_WS_URL ?? "ws://localhost:8000"}/ws/chat/${conversationId}?token=${token}`
    ws.current = new WebSocket(wsUrl)

    ws.current.onopen = () => setConnected(true)
    ws.current.onclose = () => setConnected(false)
    ws.current.onerror = () => setError("Connection error")
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "message") {
        setMessages(prev => [...prev, { role: "assistant", content: data.content, audio_url: data.audio_url }])
      } else if (data.type === "error") {
        setError(data.message)
      }
    }

    return () => ws.current?.close()
  }, [conversationId])

  const sendText = useCallback((content: string, replyWithVoice: boolean) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return
    setMessages(prev => [...prev, { role: "user", content }])
    ws.current.send(JSON.stringify({ type: "text", content, reply_with_voice: replyWithVoice }))
  }, [])

  const sendVoice = useCallback((audioBase64: string, replyWithVoice: boolean) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return
    ws.current.send(JSON.stringify({ type: "voice", audio_base64: audioBase64, reply_with_voice: replyWithVoice }))
  }, [])

  return { messages, connected, error, sendText, sendVoice }
}
```

- [ ] **Step 2: Create `frontend/src/components/MessageBubble.tsx`**

```typescript
import { ChatMessage } from "../hooks/useChat"

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${isUser ? "bg-blue-600 text-white" : "bg-white border text-gray-800"}`}>
        <p className="text-sm">{message.content}</p>
        {message.audio_url && (
          <audio controls src={message.audio_url} className="mt-2 w-full" />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create `frontend/src/components/MessageInput.tsx`**

```typescript
import { useState, useRef } from "react"

interface Props {
  onSendText: (text: string, replyWithVoice: boolean) => void
  onSendVoice: (base64: string, replyWithVoice: boolean) => void
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
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(",")[1]
        onSendVoice(base64, replyWithVoice)
      }
      reader.readAsDataURL(blob)
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
      <button onMouseDown={startRecording} onMouseUp={stopRecording}
        disabled={disabled}
        className={`px-4 py-2 rounded text-sm ${recording ? "bg-red-500 text-white" : "bg-gray-200 text-gray-700"} hover:opacity-80 disabled:opacity-50`}>
        {recording ? "Stop" : "Voice"}
      </button>
      <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
        <input type="checkbox" checked={replyWithVoice} onChange={e => setReplyWithVoice(e.target.checked)} />
        Voice reply
      </label>
    </div>
  )
}
```

- [ ] **Step 4: Create `frontend/src/pages/ChatPage.tsx`**

```typescript
import { useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useChat } from "../hooks/useChat"
import MessageBubble from "../components/MessageBubble"
import MessageInput from "../components/MessageInput"

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { messages, connected, error, sendText, sendVoice } = useChat(conversationId!)
  const bottomRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b">
        <button onClick={() => navigate("/topics")} className="text-sm text-blue-600 hover:underline">
          ← Back
        </button>
        <span className={`text-xs ${connected ? "text-green-500" : "text-red-400"}`}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2">{error}</div>}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.map((m, i) => <MessageBubble key={i} message={m} />)}
        <div ref={bottomRef} />
      </div>
      <MessageInput onSendText={sendText} onSendVoice={sendVoice} disabled={!connected} />
    </div>
  )
}
```

- [ ] **Step 5: Test manually end-to-end**

1. Register/login at http://localhost:5173/login
2. Navigate to `/topics`, click a topic
3. Type a message, verify AI response appears
4. Check "Voice reply", send message, verify audio player appears with response
5. Hold "Voice" button, speak, release — verify transcription and AI response

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useChat.ts frontend/src/components/ frontend/src/pages/ChatPage.tsx
git commit -m "feat: chat UI with WebSocket, voice recording, audio playback"
```

---

## Task 13: Docker Compose

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/audio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 3: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

- [ ] **Step 4: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: aispeaker
      POSTGRES_PASSWORD: aispeaker
      POSTGRES_DB: aispeaker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: ./backend
    depends_on:
      - postgres
      - redis
    env_file: .env
    volumes:
      - audio_data:/app/audio
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    depends_on:
      - api
    ports:
      - "80:80"

volumes:
  postgres_data:
  audio_data:
```

- [ ] **Step 5: Create root `.env.example`**

```
DATABASE_URL=postgresql+asyncpg://aispeaker:aispeaker@postgres:5432/aispeaker
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=sk-...
JWT_SECRET=change-me-in-production
AUDIO_STORAGE_PATH=/app/audio
```

- [ ] **Step 6: Build and run**

```bash
cp .env.example .env  # fill in OPENAI_API_KEY and JWT_SECRET
docker compose up --build
```

Expected: all 4 containers start, frontend accessible at http://localhost:80, API at http://localhost:8000/health

- [ ] **Step 7: Run migrations inside container**

```bash
docker compose exec api alembic upgrade head
```

Expected: migrations run successfully

- [ ] **Step 8: Full end-to-end smoke test**

1. Open http://localhost
2. Register, login
3. Topics page loads (empty — seed one via `POST /topics` with admin JWT if needed)
4. Start a conversation, send a message, receive a reply
5. Delete the conversation

- [ ] **Step 9: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml .env.example
git commit -m "feat: Docker Compose setup for local and server deployment"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Login / register | Task 3 |
| JWT auth | Task 3 |
| Topics list | Task 4 |
| Admin update topic/prompt | Task 4, Task 8 |
| Conversations (upsert, list, delete) | Task 5 |
| RAG pipeline (embed, retrieve, prompt) | Task 7 |
| WebSocket chat | Task 8 |
| Voice STT (Whisper) | Task 6 |
| Voice TTS | Task 6, Task 7 |
| Per-message reply_with_voice flag | Task 8, Task 12 |
| Redis caching (system prompt, recent window) | Task 7 |
| pgvector cosine similarity search | Task 7 |
| Error handling (WS errors, TTS fallback) | Task 8 |
| React frontend — login | Task 10 |
| React frontend — topics + conversation list | Task 11 |
| React frontend — chat UI + voice | Task 12 |
| Docker Compose | Task 13 |
| subscriptions table (stub) | Task 2 |

All spec requirements are covered.
