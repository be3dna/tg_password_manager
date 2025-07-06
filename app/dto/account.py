from dataclasses import dataclass


@dataclass
class Account:
    def __init__(self, user_id, service, login, password:bytes, password_salt:bytes):
        self._user_id = user_id
        self._service = service
        self._login = login
        self._password = password
        self._password_salt = password_salt

    def get_user_id(self):
        return self._user_id

    def get_service(self):
        return self._service

    def get_login(self):
        return self._login

    def get_password(self):
        return self._password

    def get_password_salt(self):
        return self._password_salt

    @classmethod
    def from_orm(cls, account_entity):
        return cls(
            user_id=account_entity.user_id,
            service=account_entity.service,
            login=account_entity.login,
            password=account_entity.password,
            password_salt=account_entity.password_salt
        )
