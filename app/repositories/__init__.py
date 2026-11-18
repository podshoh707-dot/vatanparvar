"""Ma'lumotlar bazasi repozitoriylari paketi."""

from app.repositories.admin_repo import AdminRepository
from app.repositories.post_repo import PostRepository
from app.repositories.schedule_repo import ScheduleRepository
from app.repositories.system_repo import SystemRepository
from app.repositories.test_repo import TestRepository
from app.repositories.user_repo import UserRepository

__all__ = [
    "AdminRepository",
    "UserRepository",
    "PostRepository",
    "TestRepository",
    "ScheduleRepository",
    "SystemRepository",
]
