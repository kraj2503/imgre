from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Create async engine with production-ready connection pool safeguards
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Ensures disconnected database handles are automatically refreshed
    future=True,
)

# Configure the sessionmaker for asynchronous database transactions
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Modern SQLAlchemy Declarative Base
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for injecting DB sessions into endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions in FastAPI route handlers."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
