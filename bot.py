"""
AVTOVATANPARVAR TESTLARI — Professional Telegram Bot Entrypoint.

Ushbu fayl loyihaning asosiy ishga tushiruvchi fayli bo'lib, Render, Koyeb, VPS
yoki lokal Windows/Linux serverlarida quyidagilarni ta'minlaydi:
1. Bir vaqtda bir nechta process ishga tushib ketishining oldini olish (PID lock).
2. UTF-8 kodlashni majburlash.
3. PostgreSQL / SQLite ma'lumotlar bazasini initsializatsiya qilish va barcha 500 ta
   rasmiy E-Avtomaktab testlarini to'liq avtomatik yuklash (auto-seed).
4. SuperAdmin va Adminlarni bazada faollashtirish.
5. Rejimni tanlash:
   - WEBHOOK_BASE_URL ko'rsatilgan bo'lsa (Render Web Service): FastAPI ilovasini uvicorn orqali yurgizadi va Webhook o'rnatadi.
   - WEBHOOK_BASE_URL bo'sh bo'lsa (Render Worker yoki lokal): Aiogram Long Polling rejimida PersistentScheduler bilan ishga tushadi.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# UTF-8 terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Root path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats

from app.config import get_settings
from app.database import db_manager
from app.main import bootstrap_database, build_dispatcher, create_app
from app.scheduler.engine import PersistentScheduler
from app.utils.logging_config import setup_logging

LOCK_FILE = os.path.join(ROOT_DIR, "bot.lock")
lock_file_handle = None


def acquire_lock():
    global lock_file_handle
    # Render, Docker va barcha bulutli container muhitlarida PID lock kerak emas
    if os.getenv("RENDER") or os.getenv("PORT"):
        return
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                content = f.read().strip()
                old_pid = int(content) if content.isdigit() else 0
            if old_pid > 0 and old_pid != os.getpid():
                try:
                    os.kill(old_pid, 0)
                except (ProcessLookupError, OSError):
                    try:
                        os.remove(LOCK_FILE)
                    except Exception:
                        pass
            else:
                try:
                    os.remove(LOCK_FILE)
                except Exception:
                    pass
        except Exception:
            pass

    try:
        lock_file_handle = open(LOCK_FILE, "w")
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
    except Exception as e:
        print(f"⚠️ Bot allaqachon ishlayapti yoki lock fayl band: {e}. Chiqilmoqda.")
        sys.exit(0)


def release_lock():
    global lock_file_handle
    if os.getenv("RENDER") or os.getenv("PORT"):
        return
    if lock_file_handle:
        try:
            if os.name == "nt":
                import msvcrt
                lock_file_handle.seek(0)
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file_handle, fcntl.LOCK_UN)
            lock_file_handle.close()
        except Exception:
            pass
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


import atexit
atexit.register(release_lock)


async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish / Bosh menyu"),
        BotCommand(command="test", description="Test ishlashni boshlash"),
        BotCommand(command="help", description="Yordam va qo'llanma"),
        BotCommand(command="cancel", description="Joriy amalni bekor qilish"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands(commands[:3], scope=BotCommandScopeAllGroupChats())
    except Exception as e:
        logging.getLogger("bot").warning(f"Standart buyruqlarni o'rnatishda xatolik: {e}")


async def run_polling():
    settings = get_settings()
    setup_logging(
        level_name=settings.LOG_LEVEL,
        secrets=[settings.BOT_TOKEN, settings.WEBHOOK_SECRET, settings.DATABASE_URL],
    )
    logger = logging.getLogger("bot")

    logger.info("AVTOVATANPARVAR TESTLARI ma'lumotlar bazasi tayyorlanmoqda...")
    db_manager.init()
    await bootstrap_database(db_manager, settings, create_tables_if_missing=True)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await set_default_commands(bot)

    scheduler = PersistentScheduler(
        session_factory=db_manager.session_factory,
        bot=bot,
        settings=settings,
    )
    dp = build_dispatcher(db=db_manager, settings=settings, scheduler=scheduler)

    await bot.delete_webhook(drop_pending_updates=False)
    await scheduler.start()

    allowed = dp.resolve_used_update_types()
    if "poll" not in allowed:
        allowed.append("poll")
    if "poll_answer" not in allowed:
        allowed.append("poll_answer")

    logger.info(
        f"✅ AVTOVATANPARVAR TESTLARI boti muvaffaqiyatli ishga tushdi!\n"
        f"👑 Super Admin: {settings.SUPERADMIN_ID}\n"
        f"📢 Asosiy kanal: {settings.CHANNEL_USERNAME}\n"
        f"🕒 Vaqt: {settings.TIMEZONE}"
    )

    try:
        await dp.start_polling(bot, allowed_updates=allowed)
    finally:
        logger.info("Bot to'xtatilmoqda...")
        await scheduler.stop()
        await bot.session.close()
        await db_manager.close()


def run_webhook():
    import uvicorn
    settings = get_settings()
    app = create_app(settings=settings, db=db_manager, create_tables_if_missing=True)
    port = int(os.getenv("PORT", settings.PORT))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=settings.LOG_LEVEL.lower())


def main():
    acquire_lock()
    settings = get_settings()
    port_env = os.getenv("PORT")
    if settings.WEBHOOK_BASE_URL or port_env:
        run_webhook()
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
