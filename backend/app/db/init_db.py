"""Database initialization utilities."""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, engine


async def init_db() -> None:
    """Create all database tables using SQLAlchemy metadata.

    This is a convenience function for development. In production,
    use Alembic migrations via `alembic upgrade head`.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all database tables. USE WITH CAUTION."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_db_connection() -> bool:
    """Verify database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def reset_db() -> None:
    """Drop and recreate all tables. Development only."""
    await drop_db()
    await init_db()


async def table_has_data(session: AsyncSession, table_name: str) -> bool:
    """Check if a table contains any rows."""
    # Validate table_name against actual database tables to prevent SQL injection
    valid_tables = await session.run_sync(
        lambda sync_session: set(inspect(sync_session.bind).get_table_names())
    )
    if table_name not in valid_tables:
        raise ValueError(f"Unknown table: {table_name!r}")

    result = await session.execute(text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)"))
    return result.scalar() or False
