from abc import ABC, abstractmethod

from app.db.account import Account
from app.db.user import User


class Repository(ABC):

    @abstractmethod
    async def save_account(self, account: Account) -> None:
        pass

    @abstractmethod
    async def get_account(self, user_id, service) -> Account | None:
        pass

    @abstractmethod
    async def get_accounts(self, user_id) -> list[str] | None:
        pass

    @abstractmethod
    async def delete_account(self, user_id, service) -> None:
        pass

    @abstractmethod
    async def add_user(self, user: User) -> None:
        pass

    @abstractmethod
    async def get_user(self, user_id) -> User | None:
        pass

    @abstractmethod
    async def verify_key(self, user_id, password_hash) -> bool:
        pass


class PostgresRepository(Repository):
    pass


class InMemoryRepository(Repository):
    def __init__(self):
        self._account_db = {"test_user": {"git": ["login", "password", "salt"]}}
        self._user_db = {"test_user": ["key", "salt"]}

    async def save_account(self, account: Account) -> None:
        entry = [account.get_login(), account.get_password(), account.get_password_salt()]
        if self._account_db.get(account.get_user_id(), None) is None:
            self._account_db[account.get_user_id()] = {account.get_service(): entry}
        else:
            self._account_db[account.get_user_id()][account.get_service()] = entry

    async def get_account(self, user_id, service) -> Account | None:
        accounts = self._account_db.get(user_id)

        if accounts is not None and accounts.get(service, None) is not None:
            account = accounts.get(service)
            return Account(user_id, service, account[0], account[1], account[2])
        else:
            return None

    async def get_accounts(self, user_id) -> list[str] | None:
        accounts = self._account_db.get(user_id)

        if not accounts:
            return None

        return list(accounts.keys())

    async def delete_account(self, user_id, service) -> None:
        accounts = self._account_db.get(user_id, None)

        if accounts is not None:
            accounts.pop(service)

    async def add_user(self, user: User) -> None:
        self._user_db[user.get_user_id()] = [user.get_password_hash(), user.get_password_hash_salt()]

    async def get_user(self, user_id) -> User | None:
        user = self._user_db[user_id]

        if user is None:
            return None

        return User(user_id, user[0], user[1])

    async def verify_key(self, user_id, password_hash) -> bool:
        return self._user_db[user_id] == password_hash
