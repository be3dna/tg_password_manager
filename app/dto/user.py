class User:
    def __init__(self, user_id, password_hash: bytes, password_hash_salt: bytes):
        self._user_id = user_id
        self._password_hash = password_hash
        self._password_hash_salt = password_hash_salt

    def get_user_id(self):
        return self._user_id

    def get_password_hash(self):
        return self._password_hash

    def get_password_hash_salt(self):
        return self._password_hash_salt

    @classmethod
    def from_orm(cls, user_entity):
        return cls(
            user_id=user_entity.user_id,
            password_hash=user_entity.password_hash,
            password_hash_salt=user_entity.password_hash_salt
        )