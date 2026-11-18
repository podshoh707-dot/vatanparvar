"""Asia/Tashkent vaqt mintaqasi bilan ishlash utilitalari."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

DEFAULT_TZ_NAME = "Asia/Tashkent"


def get_tz(tz_name: str = DEFAULT_TZ_NAME) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(DEFAULT_TZ_NAME)


def now_utc() -> datetime:
    """Hozirgi UTC vaqtini qaytaradi (timezone-aware)."""
    return datetime.now(timezone.utc)


def now_local(tz_name: str = DEFAULT_TZ_NAME) -> datetime:
    """Hozirgi mahalliy (Asia/Tashkent) vaqtni qaytaradi."""
    return now_utc().astimezone(get_tz(tz_name))


def to_local(dt: Optional[datetime], tz_name: str = DEFAULT_TZ_NAME) -> Optional[datetime]:
    """UTC yoki naive datetime'ni mahalliy vaqt mintaqasiga o'giradi."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz(tz_name))


def to_utc(dt: datetime, tz_name: str = DEFAULT_TZ_NAME) -> datetime:
    """Mahalliy yoki aware datetime'ni UTC ga o'giradi."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_tz(tz_name))
    return dt.astimezone(timezone.utc)


def format_local_dt(dt: Optional[datetime], tz_name: str = DEFAULT_TZ_NAME) -> str:
    """Sanani o'zbek foydalanuvchisi uchun qulay formatda qaytaradi."""
    local_dt = to_local(dt, tz_name)
    if local_dt is None:
        return "—"
    return local_dt.strftime("%d.%m.%Y %H:%M")


def parse_local_datetime(text: str, tz_name: str = DEFAULT_TZ_NAME) -> Optional[datetime]:
    """'DD.MM.YYYY HH:MM' yoki 'YYYY-MM-DD HH:MM' formatidagi matnni UTC datetime'ga o'giradi."""
    clean = text.strip()
    formats = (
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%d.%m.%y %H:%M",
    )
    tz = get_tz(tz_name)
    for fmt in formats:
        try:
            naive = datetime.strptime(clean, fmt)
            return naive.replace(tzinfo=tz).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


WEEKDAY_UZ = {
    0: "Du",
    1: "Se",
    2: "Chor",
    3: "Pay",
    4: "Ju",
    5: "Sha",
    6: "Yak",
}
