import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db
from app.config import settings

TEST_DB_URL = settings.database_url.replace("/aispeaker", "/aispeaker_test")

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="session")
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
