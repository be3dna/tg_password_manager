from sqlalchemy import Integer, Text, BigInteger, LargeBinary
from sqlalchemy.orm import mapped_column, Mapped

from app.entities import Base


class User(Base):
    __tablename__ = "user"

    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary)
    password_hash_salt: Mapped[bytes] = mapped_column(LargeBinary)