"""Kanal postlari va reklamalar modeli (posts jadvali)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, BigInteger, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import ContentType, PostStatus, PostType


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_type: Mapped[str] = mapped_column(
        String(16),
        default=PostType.POST.value,
        nullable=False,
        index=True,
    )
    content_type: Mapped[str] = mapped_column(
        String(16),
        default=ContentType.TEXT.value,
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    buttons_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=PostStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    channel_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    channel_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
