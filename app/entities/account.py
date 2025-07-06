from sqlalchemy import Integer, BigInteger, Text, LargeBinary, String
from sqlalchemy.orm import mapped_column, Mapped

from app.entities import Base


class Account(Base):
    __tablename__ = "account"

    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    service: Mapped[str] = mapped_column(String(255))
    login: Mapped[str] = mapped_column(String(255))
    password: Mapped[bytes] = mapped_column(LargeBinary)
    password_salt: Mapped[bytes] = mapped_column(LargeBinary)
