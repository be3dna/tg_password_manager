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