from app.db.db import sessioned
from app.entities.password import Password


class PasswordDB:
    
    @staticmethod
    @sessioned
    async def add_password(session, service, password, user_id):
        session.add(
            Password(
                user_id=user_id,
                service=service,
                password=password
            )
        )