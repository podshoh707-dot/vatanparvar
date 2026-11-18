"""Loyiha bo'ylab ishlatiladigan Enum va ruxsatlar tizimi."""

from __future__ import annotations

from enum import StrEnum


class AdminRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    TEST_MANAGER = "TEST_MANAGER"
    EDITOR = "EDITOR"
    STATISTIC_VIEWER = "STATISTIC_VIEWER"


class Permission(StrEnum):
    MANAGE_POSTS = "manage_posts"
    MANAGE_TESTS = "manage_tests"
    APPROVE_TESTS = "approve_tests"
    AUTO_PUBLISH = "auto_publish"
    MANAGE_ADS = "manage_ads"
    VIEW_STATS = "view_stats"
    MANAGE_ADMINS = "manage_admins"
    BROADCAST = "broadcast"
    MANAGE_SETTINGS = "manage_settings"
    BACKUP = "backup"
    VIEW_LOGS = "view_logs"


ROLE_PERMISSIONS: dict[AdminRole, set[Permission]] = {
    AdminRole.SUPER_ADMIN: set(Permission),
    AdminRole.ADMIN: {
        Permission.MANAGE_POSTS,
        Permission.MANAGE_TESTS,
        Permission.APPROVE_TESTS,
        Permission.AUTO_PUBLISH,
        Permission.MANAGE_ADS,
        Permission.VIEW_STATS,
        Permission.BROADCAST,
        Permission.MANAGE_SETTINGS,
        Permission.BACKUP,
        Permission.VIEW_LOGS,
    },
    AdminRole.TEST_MANAGER: {
        Permission.MANAGE_TESTS,
        Permission.APPROVE_TESTS,
        Permission.AUTO_PUBLISH,
        Permission.VIEW_STATS,
    },
    AdminRole.EDITOR: {
        Permission.MANAGE_POSTS,
        Permission.MANAGE_ADS,
        Permission.VIEW_STATS,
    },
    AdminRole.STATISTIC_VIEWER: {
        Permission.VIEW_STATS,
    },
}


def has_permission(role: str | AdminRole, permission: Permission) -> bool:
    """Berilgan rol ma'lum ruxsatga ega ekanini tekshiradi."""
    try:
        role_enum = AdminRole(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(role_enum, set())


class PostType(StrEnum):
    POST = "post"
    AD = "ad"


class ContentType(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"


class PostStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"
    PAUSED = "paused"


class TestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PublishMode(StrEnum):
    QUIZ_POLL = "quiz_poll"
    INLINE = "inline"


class PublishedTestStatus(StrEnum):
    ACTIVE = "active"
    REVEALED = "revealed"
    FAILED = "failed"


class JobType(StrEnum):
    PUBLISH_POST = "publish_post"
    PUBLISH_AD = "publish_ad"
    AUTO_TEST = "auto_test"
    REVEAL_TEST_ANSWER = "reveal_test_answer"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BroadcastStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
