
from config import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session