"""Adminlar modeli (admins jadvali)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import AdminRole, Permission, has_permission


class Admin(Base, TimestampMixin):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(
        String(32),
        default=AdminRole.EDITOR.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    def can(self, permission: Permission) -> bool:
        return self.is_active and has_permission(self.role, permission)

    @property
    def is_super_admin(self) -> bool:
        return self.is_active and self.role == AdminRole.SUPER_ADMIN.value
