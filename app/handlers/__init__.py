"""Barcha routerlarni Dispatcher'ga to'g'ri tartibda ulash."""

from __future__ import annotations

from aiogram import Dispatcher

from app.handlers.admin import (
    activity,
    admins_mgmt,
    ads,
    auto_publish,
    backup,
    broadcast,
    settings,
)
from app.handlers.common import router as common_router
from app.handlers.posts import manage as posts_manage
from app.handlers.statistics import dashboard as stats_dashboard
from app.handlers.tests import channel_interaction, manage as tests_manage
from app.handlers.user import menu as user_menu, quiz as user_quiz


def register_all_routers(dp: Dispatcher) -> None:
    """Routerlarni ustuvorlik tartibida ro'yxatdan o'tkazadi."""
    routers = [
        common_router,
        channel_interaction.router,
        posts_manage.router,
        tests_manage.router,
        auto_publish.router,
        ads.router,
        admins_mgmt.router,
        broadcast.router,
        settings.router,
        backup.router,
        activity.router,
        stats_dashboard.router,
        user_menu.router,
        user_quiz.router,
    ]
    for router in routers:
        # Testlar yoki qayta yaratilgan Dispatcher uchun eski ulanishni xavfsiz ajratish
        parent = getattr(router, "_parent_router", None)
        if parent is not None:
            if router in parent.sub_routers:
                parent.sub_routers.remove(router)
            router._parent_router = None
        dp.include_router(router)
