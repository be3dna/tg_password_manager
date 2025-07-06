from sqlalchemy import insert, select

import app.dto.account
from app.db.db import sessioned
from app.entities.account import Account as AccountEntity
from app.dto.account import Account as AccountDto


class AccountDB:

    @staticmethod
    @sessioned
    async def save_account(session, account:AccountDto):
        await session.execute(
            insert(AccountEntity)
            .values(
                user_id=account.get_user_id(),
                service=account.get_service(),
                login=account.get_login(),
                password=account.get_password(),
                password_salt=account.get_password_salt()
            )
        )
        await session.commit()

    @staticmethod
    @sessioned
    async def get_account(session, user_id, service) -> AccountDto | None:
        res = await session.execute(
            select(AccountEntity)
            .where(AccountEntity.user_id == user_id, AccountEntity.service == service)
        )
        account_entity = res.scalars().first()
        if account_entity is None:
            return None

        return AccountDto.from_orm(account_entity)

    @staticmethod
    @sessioned
    async def get_accounts(session, user_id) -> list[str] | None:
        res = await session.execute(
            select(AccountEntity.service)
            .select_from(AccountEntity)
            .where(AccountEntity.user_id == user_id)
        )
        services = res.scalars().all()
        return services

    @staticmethod
    @sessioned
    async def delete_account(session, user_id, service) -> bool:
        res = await session.execute(
            select(AccountEntity)
            .where(AccountEntity.user_id == user_id, AccountEntity.service == service)
        )
        account = res.scalars().first()
        if account is None:
            return False
        await session.delete(account)
        await session.commit()
        return True