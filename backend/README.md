# AI Speaker API

FastAPI backend for AI Speaker. Serves HTTP on port 8000 by default.

## Requirements

- Python 3.11
- PostgreSQL 16 with [pgvector](https://github.com/pgvector/pgvector)
- Redis

## Configuration

Copy the example environment file and set real values (OpenAI, JWT, AWS/S3, database, Redis).

```bash
cp .env.example .env
```

If you start Postgres and Redis with the repo’s dev Compose file (`docker-compose.dev.yml` at the repository root), use credentials that match the `postgres` service, for example:

`postgresql+asyncpg://aispeaker:aispeaker@localhost:5432/aispeaker`

## Run with Docker Compose

From the **repository root** (not `backend/`):

```bash
docker compose -f docker-compose.dev.yml up postgres redis api
```

The API is available at `http://localhost:8000`. The image runs:

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Run locally (development)

Use a virtual environment, install dependencies, apply migrations, then start Uvicorn from the `backend` directory so imports resolve.

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With Postgres and Redis already reachable per `.env`, the health check responds at `GET http://localhost:8000/health`.

## Tests

From `backend/` with the virtual environment active:

```bash
pytest
```
