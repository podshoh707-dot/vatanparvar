"""Bot ishga tushishi, FastAPI health endpointlari, webhook xavfsizligi va log masking testlari."""

from __future__ import annotations

import httpx
import pytest

from app.main import create_app
from app.utils.security import mask_sensitive_text


@pytest.mark.asyncio
async def test_root_and_health_endpoints(test_settings, db, mock_bot):
    app = create_app(
        settings=test_settings,
        db=db,
        bot=mock_bot,
        enable_scheduler=False,
        setup_webhook_on_start=True,
        create_tables_if_missing=True,
    )

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            r_root = await client.get("/")
            assert r_root.status_code == 200
            body = r_root.json()
            assert body["service"] == "AVTOVATANPARVAR TESTLARI"
            assert body["channel"] == "@AvtoVatanparvar_testlari"
            assert body["timezone"] == "Asia/Tashkent"
            assert test_settings.BOT_TOKEN not in r_root.text
            assert test_settings.WEBHOOK_SECRET not in r_root.text

            r_health = await client.get("/health")
            assert r_health.status_code == 200
            h_body = r_health.json()
            assert h_body["status"] == "ok"
            assert h_body["database"] == "connected"

    # Server ishga tushganda webhook avtomatik tiklanganini tekshirish
    mock_bot.set_webhook.assert_awaited_once()
    call_kwargs = mock_bot.set_webhook.call_args.kwargs
    assert call_kwargs["url"] == test_settings.webhook_url
    assert call_kwargs["secret_token"] == test_settings.WEBHOOK_SECRET


@pytest.mark.asyncio
async def test_webhook_security_checks(test_settings, db, mock_bot):
    app = create_app(
        settings=test_settings,
        db=db,
        bot=mock_bot,
        enable_scheduler=False,
        setup_webhook_on_start=False,
        create_tables_if_missing=True,
    )

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Noto'g'ri URL secret -> 403
            r1 = await client.post(
                "/webhook/wrong_secret",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": test_settings.WEBHOOK_SECRET},
            )
            assert r1.status_code == 403

            # 2. Header secret yo'q -> 403
            r2 = await client.post(
                f"/webhook/{test_settings.WEBHOOK_SECRET}",
                json={"update_id": 1},
            )
            assert r2.status_code == 403

            # 3. Header secret noto'g'ri -> 403
            r3 = await client.post(
                f"/webhook/{test_settings.WEBHOOK_SECRET}",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_header"},
            )
            assert r3.status_code == 403

            # 4. Yaroqsiz payload -> 400
            r4 = await client.post(
                f"/webhook/{test_settings.WEBHOOK_SECRET}",
                json={"not_an_update": True},
                headers={"X-Telegram-Bot-Api-Secret-Token": test_settings.WEBHOOK_SECRET},
            )
            assert r4.status_code == 400

            # 5. To'g'ri secret + to'g'ri Telegram update -> 200
            valid_update = {
                "update_id": 1001,
                "message": {
                    "message_id": 1,
                    "date": 1730000000,
                    "chat": {"id": 555001, "type": "private"},
                    "from": {"id": 555001, "is_bot": False, "first_name": "Ali"},
                    "text": "/start",
                },
            }
            r5 = await client.post(
                f"/webhook/{test_settings.WEBHOOK_SECRET}",
                json=valid_update,
                headers={"X-Telegram-Bot-Api-Secret-Token": test_settings.WEBHOOK_SECRET},
            )
            assert r5.status_code == 200
            assert r5.json() == {"ok": True}


def test_secret_masking_never_leaks_credentials():
    token = "123456789:AAH_real_secret_bot_token_9876543210"
    db_url = "postgresql+asyncpg://postgres:MySuperSecretPass@db.supabase.co:5432/postgres"
    raw = f"Error calling bot {token} on db {db_url}"
    masked = mask_sensitive_text(raw, [token, "MySuperSecretPass"])
    assert "AAH_real_secret_bot_token" not in masked
    assert "MySuperSecretPass" not in masked
    assert "***" in masked


def test_postgres_url_normalization_for_supabase_ssl(test_settings):
    cfg = test_settings.model_copy(
        update={
            "DATABASE_URL": "postgres://postgres:secret@aws-0-eu.pooler.supabase.com:6543/postgres?sslmode=require",
            "DB_SSL_REQUIRED": True,
        }
    )
    url, args = cfg.build_async_db_url_and_args()
    assert url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in url
    assert args.get("ssl") == "require"
    assert args.get("statement_cache_size") == 0
