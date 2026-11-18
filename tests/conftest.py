"""Pytest umumiy fixture'lar va Telegram Bot mock'lari."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

# Test muhiti uchun minimal env o'zgaruvchilar (hech qanday real token yo'q)
os.environ.setdefault("BOT_TOKEN", "999999999:TEST_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ12345")
os.environ.setdefault("SUPERADMIN_ID", "100001")
os.environ.setdefault("CHANNEL_ID", "-1001234567890")
os.environ.setdefault("CHANNEL_USERNAME", "@AvtoVatanparvar_testlari")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("WEBHOOK_BASE_URL", "https://example.onrender.com")
os.environ.setdefault("WEBHOOK_SECRET", "super_secret_test_webhook_token_1234")
os.environ.setdefault("TIMEZONE", "Asia/Tashkent")
os.environ.setdefault("DB_SSL_REQUIRED", "false")

import pytest
import pytest_asyncio

from app.config import Settings
from app.database import DatabaseManager
from app.main import bootstrap_database


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    db_file = tmp_path / "test_avtovatanparvar.db"
    return Settings(
        BOT_TOKEN="999999999:TEST_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ12345",
        SUPERADMIN_ID=100001,
        CHANNEL_ID="-1001234567890",
        CHANNEL_USERNAME="@AvtoVatanparvar_testlari",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        WEBHOOK_BASE_URL="https://example.onrender.com",
        WEBHOOK_SECRET="super_secret_test_webhook_token_1234",
        TIMEZONE="Asia/Tashkent",
        DB_SSL_REQUIRED=False,
        SCHEDULER_POLL_SECONDS=5,
    )


@pytest_asyncio.fixture
async def db(test_settings: Settings):
    manager = DatabaseManager(test_settings)
    manager.init()
    await bootstrap_database(manager, test_settings, create_tables_if_missing=True)
    yield manager
    await manager.close()


@pytest_asyncio.fixture
async def session(db: DatabaseManager):
    async with db.session_factory() as sess:
        yield sess


@pytest.fixture
def mock_bot() -> AsyncMock:
    """Telegram Bot API metodlari uchun to'liq async mock."""
    bot = AsyncMock()
    bot.id = 999999999
    bot.token = "999999999:TEST_TOKEN_ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"
    bot.session = MagicMock()
    bot.session.close = AsyncMock()

    counter = {"msg_id": 100}

    def _next_msg(**kwargs):
        counter["msg_id"] += 1
        return SimpleNamespace(
            message_id=counter["msg_id"],
            poll=SimpleNamespace(id=f"poll_{counter['msg_id']}"),
        )

    bot.get_me = AsyncMock(return_value=SimpleNamespace(id=999999999, username="avtovatanparvar_test_bot"))
    bot.get_chat_member = AsyncMock(
        return_value=SimpleNamespace(
            status="administrator",
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
        )
    )
    bot.get_chat_member_count = AsyncMock(return_value=1450)
    bot.send_message = AsyncMock(side_effect=lambda **kw: _next_msg(**kw))
    bot.send_photo = AsyncMock(side_effect=lambda **kw: _next_msg(**kw))
    bot.send_video = AsyncMock(side_effect=lambda **kw: _next_msg(**kw))
    bot.send_document = AsyncMock(side_effect=lambda **kw: _next_msg(**kw))
    bot.send_poll = AsyncMock(side_effect=lambda **kw: _next_msg(**kw))
    bot.edit_message_text = AsyncMock(return_value=True)
    bot.edit_message_caption = AsyncMock(return_value=True)
    bot.edit_message_reply_markup = AsyncMock(return_value=True)
    bot.delete_message = AsyncMock(return_value=True)
    bot.set_webhook = AsyncMock(return_value=True)
    bot.delete_webhook = AsyncMock(return_value=True)
    return bot
