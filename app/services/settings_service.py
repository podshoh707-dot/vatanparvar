"""Bot va avtomatik test joylashtirish sozlamalari servisi."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PublishMode
from app.repositories.system_repo import SystemRepository

DEFAULT_SETTINGS: dict[str, tuple[str, str, str]] = {
    "mandatory_subscription": ("false", "bool", "Foydalanuvchilar uchun kanalga majburiy obuna"),
    "auto_test_enabled": ("false", "bool", "Avtomatik test joylashtirish tizimi holati"),
    "auto_test_per_day": ("3", "int", "Kuniga avtomatik chiqariladigan testlar soni"),
    "auto_test_start_time": ("09:00", "str", "Birinchi test chiqarish vaqti (Asia/Tashkent, HH:MM)"),
    "auto_test_interval_minutes": ("180", "int", "Testlar oralig'i (daqiqa)"),
    "auto_test_weekdays": ("[0, 1, 2, 3, 4, 5, 6]", "json", "Haftaning faol kunlari (0=Du..6=Yak)"),
    "auto_test_selection_mode": ("sequential", "str", "Tanlash rejimi: sequential yoki random"),
    "auto_test_prevent_duplicates": ("true", "bool", "Takroriy test chiqarishni oldini olish"),
    "auto_test_publish_mode": (PublishMode.INLINE.value, "str", "Joylashtirish turi: inline yoki quiz_poll"),
    "auto_test_reveal_delay_minutes": ("60", "int", "Inline test javobini e'lon qilish kutish vaqti (daqiqa)"),
    "bot_welcome_text": (
        "🚦 <b>AVTOVATANPARVAR TESTLARI</b> botiga xush kelibsiz!\n\n"
        "Bu yerda siz yo'l harakati qoidalari bo'yicha bilimingizni sinab ko'rishingiz, "
        "mavzular bo'yicha test ishlashingiz va shaxsiy natijalaringizni kuzatishingiz mumkin.",
        "str",
        "Foydalanuvchilar uchun salomlashish matni",
    ),
    "bot_about_text": (
        "ℹ️ <b>AVTOVATANPARVAR TESTLARI</b>\n\n"
        "Avtomaktab o'quvchilari va haydovchilar uchun yo'l harakati qoidalari (YHQ) "
        "bo'yicha zamonaviy test va o'quv platformasi.\n\n"
        "📢 Rasmiy kanal: @AvtoVatanparvar_testlari",
        "str",
        "Bot haqida ma'lumot matni",
    ),
}


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SystemRepository(session)

    async def ensure_defaults(self) -> None:
        """Barcha standart sozlamalar bazada mavjudligini ta'minlaydi."""
        for key, (val, vtype, desc) in DEFAULT_SETTINGS.items():
            existing = await self.repo.get_setting(key)
            if existing is None:
                await self.repo.set_setting(key, val, value_type=vtype, description=desc)

    async def get_raw(self, key: str) -> str:
        item = await self.repo.get_setting(key)
        if item is not None:
            return item.value
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key][0]
        return ""

    async def get_bool(self, key: str, default: bool = False) -> bool:
        raw = await self.get_raw(key)
        if not raw:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "ha", "on"}

    async def get_int(self, key: str, default: int = 0) -> int:
        raw = await self.get_raw(key)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    async def get_json(self, key: str, default: Any = None) -> Any:
        raw = await self.get_raw(key)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    async def set_value(
        self,
        key: str,
        value: Any,
        *,
        updated_by: Optional[int] = None,
    ) -> None:
        meta = DEFAULT_SETTINGS.get(key)
        vtype = meta[1] if meta else "str"
        desc = meta[2] if meta else None

        if isinstance(value, bool):
            serialized = "true" if value else "false"
            vtype = "bool"
        elif isinstance(value, (list, dict)):
            serialized = json.dumps(value)
            vtype = "json"
        elif isinstance(value, int):
            serialized = str(value)
            vtype = "int"
        else:
            serialized = str(value)

        await self.repo.set_setting(
            key,
            serialized,
            value_type=vtype,
            description=desc,
            updated_by=updated_by,
        )

    async def get_auto_publish_config(self) -> dict[str, Any]:
        """Avtomatik test joylashtirishning barcha sozlamalarini bir joyda qaytaradi."""
        return {
            "enabled": await self.get_bool("auto_test_enabled", False),
            "per_day": await self.get_int("auto_test_per_day", 3),
            "start_time": (await self.get_raw("auto_test_start_time")) or "09:00",
            "interval_minutes": await self.get_int("auto_test_interval_minutes", 180),
            "weekdays": await self.get_json("auto_test_weekdays", [0, 1, 2, 3, 4, 5, 6]),
            "selection_mode": (await self.get_raw("auto_test_selection_mode")) or "sequential",
            "prevent_duplicates": await self.get_bool("auto_test_prevent_duplicates", True),
            "publish_mode": (await self.get_raw("auto_test_publish_mode")) or PublishMode.INLINE.value,
            "reveal_delay_minutes": await self.get_int("auto_test_reveal_delay_minutes", 60),
        }
