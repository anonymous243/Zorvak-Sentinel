import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("Tests must run against real PostgreSQL database. SQLite is forbidden.")

@pytest_asyncio.fixture(scope="session")
async def pg_engine():
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"statement_cache_size": 0},
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
def session_factory(pg_engine):
    return async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s
        # Ensure rollback any open transaction to maintain test isolation
        try:
            await s.rollback()
        except Exception:
            pass
