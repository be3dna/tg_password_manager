from sqlalchemy import BigInteger, Integer, Text, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from app.entities.base import Base


class Password(Base):
    __tablename__ = 'password'

    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    service: Mapped[str] = mapped_column(Text)
    password: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint('service', 'user_id', name='uix_title_user'),)
