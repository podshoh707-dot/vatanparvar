"""Test savollari, e'lon qilingan testlar, javoblar va urinishlar modellari."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import Difficulty, PublishedTestStatus, PublishMode, TestStatus
from app.utils.timezone import now_utc


class TestQuestion(Base, TimestampMixin):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(512), nullable=False)
    option_b: Mapped[str] = mapped_column(String(512), nullable=False)
    option_c: Mapped[str] = mapped_column(String(512), nullable=False)
    option_d: Mapped[str] = mapped_column(String(512), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(128), default="Umumiy", nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(
        String(16),
        default=Difficulty.MEDIUM.value,
        nullable=False,
        index=True,
    )
    image_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=TestStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    approved_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    times_published: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    published_instances: Mapped[list["PublishedTest"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class PublishedTest(Base):
    __tablename__ = "published_tests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("test_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    poll_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    mode: Mapped[str] = mapped_column(
        String(24),
        default=PublishMode.INLINE.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default=PublishedTestStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    reveal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revealed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reveal_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wrong_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
        index=True,
    )

    question: Mapped[TestQuestion] = relationship(back_populates="published_instances")


class TestAnswer(Base):
    """Kanaldagi inline testga foydalanuvchi javobi (har bir testga faqat 1 marta!)."""

    __tablename__ = "test_answers"
    __table_args__ = (
        UniqueConstraint(
            "published_test_id",
            "user_telegram_id",
            name="uq_test_answers_published_user",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    published_test_id: Mapped[int] = mapped_column(
        ForeignKey("published_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("test_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    selected_option: Mapped[str] = mapped_column(String(1), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
    )


class TestAttempt(Base):
    """Oddiy foydalanuvchining bot ichida test yechish urinishlari."""

    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("test_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(32), default="bot_practice", nullable=False)
    selected_option: Mapped[str] = mapped_column(String(1), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        nullable=False,
        index=True,
    )
