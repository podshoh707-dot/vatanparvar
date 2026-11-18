"""Sozlamalar, faoliyat tarixi, ommaviy xabarlar va zaxira nusxalar modellari."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import BroadcastStatus, ContentType
from app.utils.timezone import now_utc


class BotSetting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(24), default="str", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
    )


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
        index=True,
    )


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(
        String(16),
        default=ContentType.TEXT.value,
        nullable=False,
    )
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    buttons_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=BroadcastStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    total_targets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
    )


class BackupHistory(Base):
    __tablename__ = "backup_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backup_type: Mapped[str] = mapped_column(String(24), default="manual", nullable=False)
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tables_included: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    record_counts_json: Mapped[Optional[dict[str, int]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="completed", nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
    )
