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
            chore_columns = await conn.execute(text("PRAGMA table_info(chores)"))
            chore_column_names = {row[1] for row in chore_columns.fetchall()}

            if "room" not in chore_column_names:
                await conn.execute(
                    text("ALTER TABLE chores ADD COLUMN room VARCHAR(100) NOT NULL DEFAULT 'General'")
                )

            child_columns = await conn.execute(text("PRAGMA table_info(children)"))
            child_column_names = {row[1] for row in child_columns.fetchall()}

            if "goal_reward_id" not in child_column_names:
                await conn.execute(
                    text("ALTER TABLE children ADD COLUMN goal_reward_id INTEGER")
                )

            if "game_tickets" not in child_column_names:
                await conn.execute(
                    text("ALTER TABLE children ADD COLUMN game_tickets INTEGER NOT NULL DEFAULT 0")
                )

            if "treasure_high_score" not in child_column_names:
                await conn.execute(
                    text("ALTER TABLE children ADD COLUMN treasure_high_score INTEGER NOT NULL DEFAULT 0")
                )

            if "game_round_ready" not in child_column_names:
                await conn.execute(
                    text("ALTER TABLE children ADD COLUMN game_round_ready BOOLEAN NOT NULL DEFAULT 0")
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
