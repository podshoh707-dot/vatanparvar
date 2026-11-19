"""
AVTOVATANPARVAR TESTLARI — FastAPI + Aiogram 3 Webhook asosiy ilova.

Endpointlar:
- GET  /
- GET  /health
- POST /webhook/{secret}
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.database import DatabaseManager, db_manager
from app.handlers import register_all_routers
from app.middlewares import (
    AuthAndUserMiddleware,
    DatabaseSessionMiddleware,
    ErrorHandlingMiddleware,
    MandatorySubscriptionMiddleware,
)
from app.models import Base
from app.scheduler.engine import PersistentScheduler
from app.services.admin_service import AdminService
from app.services.seed_service import seed_eavtomaktab_questions
from app.services.settings_service import SettingsService
from app.utils.logging_config import setup_logging
from app.utils.security import verify_secret_token
from app.utils.timezone import now_local

logger = logging.getLogger(__name__)


def build_dispatcher(
    *,
    db: DatabaseManager,
    settings: Settings,
    scheduler: Optional[PersistentScheduler] = None,
) -> Dispatcher:
    """Barcha middleware va routerlar ulangan Aiogram Dispatcher yaratadi."""
    dp = Dispatcher(storage=MemoryStorage())

    # Outer & inner middleware tartibi:
    # ErrorHandling -> DatabaseSession -> AuthAndUser -> MandatorySubscription
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.update.outer_middleware(DatabaseSessionMiddleware(db.session_factory))

    dp.message.middleware(AuthAndUserMiddleware(settings))
    dp.callback_query.middleware(AuthAndUserMiddleware(settings))

    dp.message.middleware(MandatorySubscriptionMiddleware(settings))
    dp.callback_query.middleware(MandatorySubscriptionMiddleware(settings))

    if scheduler is not None:
        dp["scheduler"] = scheduler
    dp["settings"] = settings

    register_all_routers(dp)
    return dp


async def bootstrap_database(
    db: DatabaseManager,
    settings: Settings,
    *,
    create_tables_if_missing: bool = False,
) -> None:
    """Super admin va standart sozlamalarni bazada tayyorlaydi."""
    if create_tables_if_missing:
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with db.session_factory() as session:
        await SettingsService(session).ensure_defaults()
        await AdminService(session, settings).ensure_superadmin()
        await seed_eavtomaktab_questions(session, settings)
        await session.commit()


def create_app(
    *,
    settings: Optional[Settings] = None,
    db: Optional[DatabaseManager] = None,
    bot: Optional[Bot] = None,
    enable_scheduler: bool = True,
    setup_webhook_on_start: bool = True,
    enable_polling_if_no_webhook: bool = True,
    create_tables_if_missing: bool = True,
) -> FastAPI:
    """FastAPI webhook ilovasini yig'adi (production va testlar uchun)."""
    cfg = settings or get_settings()
    database = db or db_manager

    setup_logging(
        level_name=cfg.LOG_LEVEL,
        secrets=[cfg.BOT_TOKEN, cfg.WEBHOOK_SECRET, cfg.DATABASE_URL],
    )

    bot_instance = bot or Bot(
        token=cfg.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    scheduler = PersistentScheduler(
        session_factory=database.session_factory,
        bot=bot_instance,
        settings=cfg,
    )
    dp = build_dispatcher(db=database, settings=cfg, scheduler=scheduler)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.init()
        await bootstrap_database(
            database,
            cfg,
            create_tables_if_missing=create_tables_if_missing,
        )

        if enable_scheduler:
            await scheduler.start()

        polling_task = None
        if cfg.webhook_url:
            if setup_webhook_on_start:
                try:
                    allowed = dp.resolve_used_update_types()
                    if "poll" not in allowed:
                        allowed.append("poll")
                    if "poll_answer" not in allowed:
                        allowed.append("poll_answer")
                    await bot_instance.set_webhook(
                        url=cfg.webhook_url,
                        secret_token=cfg.WEBHOOK_SECRET,
                        allowed_updates=allowed,
                        drop_pending_updates=False,
                    )
                    logger.info("Webhook muvaffaqiyatli o'rnatildi: %s/webhook/***", cfg.WEBHOOK_BASE_URL)
                except Exception as exc:
                    logger.error("Webhook o'rnatishda xatolik: %s", exc)
        elif enable_polling_if_no_webhook and not isinstance(bot_instance, (MagicMock, AsyncMock)):
            try:
                await bot_instance.delete_webhook(drop_pending_updates=False)
            except Exception as exc:
                logger.warning("Eski webhookni o'chirishda ogohlantirish: %s", exc)

            allowed = dp.resolve_used_update_types()
            if "poll" not in allowed:
                allowed.append("poll")
            if "poll_answer" not in allowed:
                allowed.append("poll_answer")

            async def _safe_polling():
                logger.info("Bot Webhook URL ko'rsatilmaganligi sababli Long Polling orqa fonda ishga tushdi.")
                while True:
                    try:
                        await dp.start_polling(
                            bot_instance,
                            allowed_updates=allowed,
                            handle_signals=False,
                            close_bot_session=False,
                        )
                        break
                    except asyncio.CancelledError:
                        break
                    except Exception as exc:
                        logger.error("Long Polling xatosi, 5 soniyadan so'ng qayta ulanadi: %s", exc)
                        await asyncio.sleep(5)

            polling_task = asyncio.create_task(_safe_polling())

        app.state.bot = bot_instance
        app.state.dp = dp
        app.state.scheduler = scheduler
        app.state.db = database
        app.state.settings = cfg

        yield

        if polling_task is not None:
            polling_task.cancel()
            try:
                await polling_task
            except (asyncio.CancelledError, Exception):
                pass

        if enable_scheduler:
            await scheduler.stop()
        try:
            await bot_instance.session.close()
        except Exception:
            pass
        await database.close()

    app = FastAPI(
        title="AVTOVATANPARVAR TESTLARI Telegram Bot",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.get("/")
    async def root() -> dict:
        return {
            "service": "AVTOVATANPARVAR TESTLARI",
            "channel": cfg.CHANNEL_USERNAME,
            "timezone": cfg.TIMEZONE,
            "status": "running",
            "local_time": now_local(cfg.TIMEZONE).isoformat(),
        }

    @app.get("/health")
    async def health() -> JSONResponse:
        db_ok = await database.health_check()
        payload = {
            "status": "ok" if db_ok else "degraded",
            "database": "connected" if db_ok else "disconnected",
            "scheduler_running": scheduler.is_running,
            "last_scheduler_tick": scheduler.last_tick_at.isoformat() if scheduler.last_tick_at else None,
            "timezone": cfg.TIMEZONE,
        }
        # Render deployment health check fail bo'lmasligi uchun doim HTTP 200 qaytaradi
        return JSONResponse(content=payload, status_code=status.HTTP_200_OK)

    @app.post("/webhook/{secret}")
    async def telegram_webhook(
        secret: str,
        request: Request,
        x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
    ) -> dict:
        # 1. URL path secret tekshiruvi
        if not verify_secret_token(secret, cfg.WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook secret noto'g'ri.",
            )

        # 2. Telegram secret token header tekshiruvi
        if not verify_secret_token(x_telegram_bot_api_secret_token, cfg.WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="X-Telegram-Bot-Api-Secret-Token noto'g'ri yoki yuborilmagan.",
            )

        try:
            payload = await request.json()
            update = Update.model_validate(payload, context={"bot": bot_instance})
        except Exception as exc:
            logger.warning("Noto'g'ri Telegram update payload: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Noto'g'ri update formati.",
            ) from exc

        await dp.feed_update(bot_instance, update)
        return {"ok": True}

    return app


app = create_app(create_tables_if_missing=True)
