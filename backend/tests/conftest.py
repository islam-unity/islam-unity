import os
os.environ["USE_OFFLINE_EMBEDDING"] = "true"
import asyncio
import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.seed_data import seed_database
from app.core.security import create_access_token

CONFTEST_DB_FILE = "./test_conftest_isolated.db"
CONFTEST_DB_URL = f"sqlite+aiosqlite:///{CONFTEST_DB_FILE}"

test_engine = create_async_engine(
    CONFTEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


_db_initialized = False


async def _init_conftest_db():
    global _db_initialized
    if not _db_initialized:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with TestSessionLocal() as session:
            await seed_database(session)
        _db_initialized = True


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    if os.path.exists(CONFTEST_DB_FILE):
        try:
            os.remove(CONFTEST_DB_FILE)
        except OSError:
            pass

    await _init_conftest_db()
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    await test_engine.dispose()
    if os.path.exists(CONFTEST_DB_FILE):
        try:
            os.remove(CONFTEST_DB_FILE)
        except OSError:
            pass


@pytest_asyncio.fixture
async def client():
    await _init_conftest_db()
    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db_session():
    await _init_conftest_db()
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def seeker_auth_headers():
    token = create_access_token(subject="usr_seeker_1", role="SEEKER")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def scholar_auth_headers():
    token = create_access_token(subject="usr_scholar_1", role="SCHOLAR")
    return {"Authorization": f"Bearer {token}"}
