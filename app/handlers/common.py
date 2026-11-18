"""Umumiy /start, navigatsiya, bekor qilish va ruxsat tekshirish handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.keyboards.admin import admin_main_menu_kb
from app.keyboards.ads import ads_menu_kb
from app.keyboards.common import BTN_BACK, BTN_CANCEL, BTN_MAIN_MENU
from app.keyboards.posts import posts_menu_kb
from app.keyboards.tests import tests_menu_kb
from app.keyboards.users import user_main_menu_kb
from app.models.admin import Admin
from app.models.enums import Permission
from app.services.settings_service import SettingsService
from app.utils.formatting import ROLE_LABELS

router = Router(name="common")


async def require_permission(
    event: Message | CallbackQuery,
    admin: Optional[Admin],
    permission: Optional[Permission] = None,
) -> bool:
    """Admin va uning aniq rol ruxsatini tekshiradi. Ruxsat bo'lmasa xabar beradi."""
    if admin is None or not admin.is_active:
        msg = "⛔ Sizda admin huquqlari mavjud emas."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return False

    if permission is not None and not admin.can(permission):
        role_txt = ROLE_LABELS.get(admin.role, admin.role)
        msg = f"⛔ Sizning rolingiz ({role_txt}) bu bo'limdan foydalanishga ruxsat bermaydi."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return False

    return True


def _admin_welcome_text(admin: Admin) -> str:
    cfg = get_settings()
    role_txt = ROLE_LABELS.get(admin.role, admin.role)
    return (
        "🛡 <b>AVTOVATANPARVAR TESTLARI — ADMIN PANEL</b>\n\n"
        f"👤 Rolingiz: <b>{role_txt}</b>\n"
        f"📢 Asosiy kanal: <b>{cfg.CHANNEL_USERNAME}</b>\n"
        f"🕒 Vaqt mintaqasi: <b>{cfg.TIMEZONE}</b>\n\n"
        "Kerakli boshqaruv bo'limini quyidagi menyudan tanlang:"
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    await state.clear()
    if admin is not None and admin.is_active:
        await message.answer(
            _admin_welcome_text(admin),
            parse_mode="HTML",
            reply_markup=admin_main_menu_kb(),
        )
        return

    settings_svc = SettingsService(session)
    welcome_text = await settings_svc.get_raw("bot_welcome_text")
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=user_main_menu_kb(),
    )


@router.message(Command("cancel"))
@router.message(F.text == BTN_CANCEL)
async def handle_cancel_text(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    await state.clear()
    if admin and admin.is_active:
        await message.answer(
            "❌ Joriy amal bekor qilindi. Bosh admin menyuga qaytdingiz.",
            reply_markup=admin_main_menu_kb(),
        )
    else:
        await message.answer(
            "❌ Amal bekor qilindi.",
            reply_markup=user_main_menu_kb(),
        )


@router.message(F.text.in_({BTN_MAIN_MENU, BTN_BACK}))
async def handle_back_or_home(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    await state.clear()
    if admin and admin.is_active:
        await message.answer(
            _admin_welcome_text(admin),
            parse_mode="HTML",
            reply_markup=admin_main_menu_kb(),
        )
    else:
        await message.answer(
            "🏠 Bosh sahifaga qaytdingiz.",
            reply_markup=user_main_menu_kb(),
        )


@router.callback_query(F.data == "nav:cancel")
async def cb_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi")
    if callback.message:
        if admin and admin.is_active:
            await callback.message.answer(
                "❌ Amal bekor qilindi.",
                reply_markup=admin_main_menu_kb(),
            )
        else:
            await callback.message.answer(
                "❌ Amal bekor qilindi.",
                reply_markup=user_main_menu_kb(),
            )


@router.callback_query(F.data == "nav:admin_home")
async def cb_admin_home(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin):
        return
    await state.clear()
    await callback.answer()
    assert admin is not None
    if callback.message:
        await callback.message.answer(
            _admin_welcome_text(admin),
            parse_mode="HTML",
            reply_markup=admin_main_menu_kb(),
        )


@router.callback_query(F.data == "nav:posts_menu")
async def cb_posts_menu(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "📝 <b>POSTLARNI BOSHQARISH</b>\nKerakli amalni tanlang:",
            parse_mode="HTML",
            reply_markup=posts_menu_kb(),
        )


@router.callback_query(F.data == "nav:tests_menu")
async def cb_tests_menu(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "🚦 <b>TESTLARNI BOSHQARISH</b>\nKerakli amalni tanlang:",
            parse_mode="HTML",
            reply_markup=tests_menu_kb(),
        )


@router.callback_query(F.data == "nav:ads_menu")
async def cb_ads_menu(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "📢 <b>REKLAMA BOSHQARUVI</b>\nKerakli amalni tanlang:",
            parse_mode="HTML",
            reply_markup=ads_menu_kb(),
        )


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()
