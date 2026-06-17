import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Database URL - using SQLite with aiosqlite for async support
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./instance/chore.db")


def ensure_sqlite_directory(database_url: str) -> None:
    """Create the SQLite parent directory when using a file-backed database."""
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        return
    if url.database == ":memory:":
        return
    Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)


ensure_sqlite_directory(DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables if they don't exist."""
    from app.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.drivername.startswith("sqlite"):
            columns = await conn.execute(text("PRAGMA table_info(chores)"))
            column_names = {row[1] for row in columns.fetchall()}
            if "room" not in column_names:
                await conn.execute(
                    text("ALTER TABLE chores ADD COLUMN room VARCHAR(100) NOT NULL DEFAULT 'General'")
                )


async def get_db():
    """Dependency for getting a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
