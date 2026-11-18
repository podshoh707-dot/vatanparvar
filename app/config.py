"""Ilova konfiguratsiyasi (Environment Variables orqali)."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha muhit o'zgaruvchilari va loyiha sozlamalari."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    BOT_TOKEN: str = Field(..., min_length=10, description="Telegram Bot tokeni")
    SUPERADMIN_ID: int = Field(default=8781024332, gt=0, description="Asosiy Super Admin Telegram ID")
    ADMIN_IDS: str = Field(default="8781024332,8528538777", description="Adminlar ID ro'yxati (vergul bilan)")
    CHANNEL_ID: str = Field(
        default="@AvtoVatanparvar_testlari",
        description="Kanal ID (-100...) yoki @username",
    )
    CHANNEL_USERNAME: str = Field(
        default="@AvtoVatanparvar_testlari",
        description="Kanal username manzili",
    )
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./local_dev.db",
        description="PostgreSQL (asyncpg) ulanish URL manzili",
    )
    WEBHOOK_BASE_URL: str = Field(
        default="",
        description="Render Web Service asosiy URL manzili",
    )
    WEBHOOK_SECRET: str = Field(
        default="change-me-webhook-secret-token",
        min_length=8,
        description="Webhook himoya kaliti",
    )
    TIMEZONE: str = Field(
        default="Asia/Tashkent",
        description="Asosiy vaqt mintaqasi",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Loglash darajasi")
    SCHEDULER_POLL_SECONDS: int = Field(
        default=20,
        ge=5,
        le=300,
        description="Rejalashtirilgan vazifalarni tekshirish oralig'i (soniya)",
    )
    DB_SSL_REQUIRED: bool = Field(
        default=True,
        description="PostgreSQL uchun SSL ulanishni majburlash",
    )
    PORT: int = Field(default=8000, ge=1, le=65535)

    @field_validator("CHANNEL_USERNAME")
    @classmethod
    def normalize_channel_username(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            return "@AvtoVatanparvar_testlari"
        if not clean.startswith("@"):
            clean = f"@{clean}"
        return clean

    @field_validator("WEBHOOK_BASE_URL")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @property
    def admin_id_list(self) -> list[int]:
        ids: list[int] = [self.SUPERADMIN_ID]
        if self.ADMIN_IDS:
            for item in str(self.ADMIN_IDS).split(","):
                item_s = item.strip()
                if item_s.isdigit():
                    val = int(item_s)
                    if val not in ids:
                        ids.append(val)
        return ids

    @property
    def channel_target(self) -> int | str:
        """Kanal ID butun son bo'lsa int, aks holda @username qaytaradi."""
        raw = str(self.CHANNEL_ID).strip()
        if raw.lstrip("-").isdigit():
            return int(raw)
        return raw if raw.startswith("@") else f"@{raw}"

    @property
    def channel_url(self) -> str:
        """Kanalning to'liq havolasi."""
        username = self.CHANNEL_USERNAME.lstrip("@")
        return f"https://t.me/{username}"

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.WEBHOOK_SECRET}"

    @property
    def webhook_url(self) -> str:
        if not self.WEBHOOK_BASE_URL:
            return ""
        return f"{self.WEBHOOK_BASE_URL}{self.webhook_path}"

    def build_async_db_url_and_args(self) -> tuple[str, dict]:
        """PostgreSQL (Render/Supabase) yoki SQLite uchun async URL va connect_args tayyorlaydi."""
        url = self.DATABASE_URL.strip()

        if url.startswith("sqlite"):
            if url.startswith("sqlite:///") and "+aiosqlite" not in url:
                url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
            return url, {}

        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        parsed = urlparse(url)
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        sslmode = query_params.pop("sslmode", None)
        query_params.pop("channel_binding", None)

        clean_query = urlencode(query_params)
        clean_url = urlunparse(parsed._replace(query=clean_query))

        connect_args: dict = {}
        host = (parsed.hostname or "").lower()
        is_local = host in {"localhost", "127.0.0.1", "::1"}

        use_ssl = False
        if sslmode and sslmode.lower() not in {"disable", "allow"}:
            use_ssl = True
        elif self.DB_SSL_REQUIRED and not is_local:
            use_ssl = True

        if use_ssl:
            connect_args["ssl"] = "require"

        # Supabase PgBouncer transaction pooler uchun prepared statements o'chiriladi
        if "pooler.supabase.com" in host or (parsed.port == 6543):
            connect_args["statement_cache_size"] = 0

        return clean_url, connect_args


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Sozlamalar singleton nusxasini qaytaradi."""
    return Settings()
