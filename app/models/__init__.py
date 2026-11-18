"""Barcha ORM modellarni bitta joydan eksport qilish."""

from app.models.admin import Admin
from app.models.base import Base
from app.models.post import Post
from app.models.schedule import ScheduledJob
from app.models.system import ActivityLog, BackupHistory, BotSetting, Broadcast
from app.models.test import PublishedTest, TestAnswer, TestAttempt, TestQuestion
from app.models.user import User

__all__ = [
    "Base",
    "Admin",
    "User",
    "Post",
    "TestQuestion",
    "PublishedTest",
    "TestAnswer",
    "TestAttempt",
    "ScheduledJob",
    "BotSetting",
    "ActivityLog",
    "Broadcast",
    "BackupHistory",
]
