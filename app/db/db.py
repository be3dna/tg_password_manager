from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL


engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def sessioned(f):
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            async with session.begin():
                res = await f(session, *args, **kwargs)
            await session.commit()
        return res
    return wrapper