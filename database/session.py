from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config import config

# PostgreSQL async URL
DATABASE_URL = config.DATABASE_URL  # example: "postgresql+asyncpg://user:pass@localhost:5432/dbname"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency for fast use in handlers/services
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
