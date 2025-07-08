from sqlalchemy import insert, select

from app.db.db import sessioned
from app.dto.user import User as UserDto
from app.entities.user import User as UserEntity


class UserDB:

    @staticmethod
    @sessioned
    async def add_user(session, user: UserDto) -> None:
        await session.execute(
            insert(UserEntity)
            .values(
                user_id=user.get_user_id(),
                password_hash=user.get_password_hash(),
                password_hash_salt=user.get_password_hash_salt()
            )
        )
        await session.commit()

    @staticmethod
    @sessioned
    async def get_user(session, user_id) -> UserDto | None:
        res = await session.execute(
            select(UserEntity)
            .select_from(UserEntity)
            .where(UserEntity.user_id == user_id)
        )
        user_entity = res.scalars().first()
        if user_entity is None:
            return None

        return UserDto.from_orm(user_entity)

