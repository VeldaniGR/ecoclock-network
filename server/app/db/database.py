"""Conexión asíncrona a BD con SQLAlchemy."""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://"), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependencia de FastAPI para inyectar sesión de BD."""
    async with AsyncSessionLocal() as session:
        yield session
