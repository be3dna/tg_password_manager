from sqlalchemy import delete, insert, select

from app.db.db import sessioned
from app.entities.password import Password


class PasswordDB:
    
    @staticmethod
    @sessioned
    async def add_password(session, service, password, user_id):
        await session.execute(
            insert(Password)
            .values(
                user_id=user_id,
                service=service,
                password=password
            )
        )
        await session.commit()


    @staticmethod
    @sessioned
    async def get_user_services(session, user_id):
        res = await session.execute(
            select(Password.service)
            .select_from(Password)
            .where(Password.user_id == user_id)
        )
        services = res.scalars().all()
        return services


    @staticmethod
    @sessioned
    async def get_password(session, user_id, service):
        res = await session.execute(
            select(Password.password)
            .select_from(Password)
            .where(Password.user_id == user_id, Password.service == service)
        )
        password = res.scalars().first()
        return password
    
    @staticmethod
    @sessioned
    async def delete_password(session, user_id, service):
        await session.execute(
            delete(Password)
            .where(Password.user_id == user_id, Password.service == service)
        )
        await session.commit()
