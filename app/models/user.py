"""Bot foydalanuvchilari modeli (users jadvali)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.utils.timezone import now_utc


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
    )

    @property
    def display_name(self) -> str:
        parts = [p for p in [self.first_name, self.last_name] if p]
        if parts:
            return " ".join(parts)
        if self.username:
            return f"@{self.username}"
        return str(self.telegram_id)
