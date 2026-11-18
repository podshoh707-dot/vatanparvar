"""Reklama tizimi boshqaruvi handlerlari."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.ads import (
    BTN_AD_CREATE,
    BTN_AD_DELETE,
    BTN_AD_EDIT,
    BTN_AD_HISTORY,
    BTN_AD_PAUSE,
    BTN_AD_SCHEDULE,
    ad_detail_kb,
    ads_list_kb,
    ads_menu_kb,
)
from app.keyboards.common import BTN_ADMIN_ADS, BTN_SKIP, cancel_only_kb
from app.keyboards.posts import post_confirm_kb, post_delete_confirm_kb, post_schedule_confirm_kb
from app.models.admin import Admin
from app.models.enums import ContentType, Permission, PostStatus, PostType
from app.repositories.post_repo import PostRepository
from app.services.channel_service import ChannelService, explain_telegram_error
from app.services.post_service import PostService
from app.utils.formatting import STATUS_LABELS
from app.utils.fsm import AdCreateState, AdEditState
from app.utils.security import escape_html, parse_inline_buttons_text
from app.utils.timezone import format_local_dt, now_utc, parse_local_datetime

router = Router(name="admin_ads")
PAGE_SIZE = 8


@router.message(F.text == BTN_ADMIN_ADS)
async def open_ads_menu(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await state.clear()
    await message.answer(
        "📢 <b>REKLAMA BOSHQARUVI</b>\n\n"
        "Matnli, rasmli, videoli va inline tugmali reklamalarni yarating, "
        "vaqtga rejalashtiring, tahrirlang yoki vaqtincha to'xtating.",
        parse_mode="HTML",
        reply_markup=ads_menu_kb(),
    )


@router.message(F.text.in_({BTN_AD_CREATE, BTN_AD_SCHEDULE}))
async def start_create_ad(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await state.clear()
    force_schedule = message.text == BTN_AD_SCHEDULE
    await state.set_state(AdCreateState.waiting_content)
    await state.update_data(force_schedule=force_schedule)
    await message.answer(
        "📢 <b>Yangi reklama kontenti</b>\n\n"
        "Reklama xabarini yuboring: oddiy matn, rasm (caption bilan) yoki video (caption bilan). "
        "HTML formatlash qo'llab-quvvatlanadi.",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(),
    )


@router.message(AdCreateState.waiting_content)
async def receive_ad_content(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return

    if message.photo:
        ctype = ContentType.PHOTO
        media_id = message.photo[-1].file_id
        text = message.html_text if message.caption else ""
    elif message.video:
        ctype = ContentType.VIDEO
        media_id = message.video.file_id
        text = message.html_text if message.caption else ""
    elif message.document:
        ctype = ContentType.DOCUMENT
        media_id = message.document.file_id
        text = message.html_text if message.caption else ""
    elif message.text:
        ctype = ContentType.TEXT
        media_id = None
        text = message.html_text or message.text
    else:
        await message.answer("⚠️ Iltimos, matn, rasm, video yoki hujjat yuboring.")
        return

    await state.update_data(content_type=ctype.value, text=text, media_file_id=media_id)
    await state.set_state(AdCreateState.waiting_buttons)
    await message.answer(
        "🔗 <b>Reklama tugmalari (ixtiyoriy)</b>\n\n"
        "Har bir qatorda: <code>Tugma matni | https://havola</code>\n"
        "Yoki <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(allow_skip=True),
    )


@router.message(AdCreateState.waiting_buttons)
async def receive_ad_buttons(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return

    buttons_json: list[dict[str, str]] = []
    if message.text and message.text.strip() != BTN_SKIP:
        buttons_json, errors = parse_inline_buttons_text(message.text)
        if errors:
            await message.answer("⚠️ Xatolar:\n" + "\n".join(f"• {e}" for e in errors))
            return

    await state.update_data(buttons_json=buttons_json)
    data = await state.get_data()

    await message.answer("👁 <b>Reklamaning oldindan ko'rinishi:</b>", parse_mode="HTML")
    try:
        await ChannelService(bot).send_content(
            chat_id=message.chat.id,
            content_type=data["content_type"],
            text=data.get("text"),
            media_file_id=data.get("media_file_id"),
            buttons_json=buttons_json,
        )
    except Exception as exc:
        await message.answer(f"⚠️ Oldindan ko'rsatishda xato: {escape_html(explain_telegram_error(exc))}", parse_mode="HTML")
        await state.set_state(AdCreateState.waiting_content)
        return

    if data.get("force_schedule"):
        cfg = get_settings()
        await state.set_state(AdCreateState.waiting_schedule_time)
        await message.answer(
            f"📅 Reklama chiqarish vaqtini kiriting ({cfg.TIMEZONE}):\n<code>KK.OO.YYYY SS:DD</code>",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )
        return

    await state.set_state(AdCreateState.confirm)
    await message.answer("Reklamani kanalga joylash yoki rejalashtirishni tanlang:", reply_markup=post_confirm_kb(is_ad=True))


@router.callback_query(AdCreateState.confirm, F.data == "ad:confirm_now")
async def cb_ad_publish_now(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    assert admin is not None
    d = await state.get_data()
    post, msg = await PostService(session, bot).publish_now(
        created_by=admin.telegram_id,
        post_type=PostType.AD,
        content_type=ContentType(d["content_type"]),
        text=d.get("text"),
        media_file_id=d.get("media_file_id"),
        buttons_json=d.get("buttons_json") or None,
    )
    await state.clear()
    await callback.answer()
    icon = "✅" if post else "⚠️"
    if callback.message:
        await callback.message.answer(f"{icon} {escape_html(msg)}", parse_mode="HTML", reply_markup=ads_menu_kb())


@router.callback_query(AdCreateState.confirm, F.data == "ad:choose_schedule")
async def cb_ad_choose_schedule(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    await state.set_state(AdCreateState.waiting_schedule_time)
    await callback.answer()
    cfg = get_settings()
    if callback.message:
        await callback.message.answer(
            f"📅 Reklama vaqtini kiriting ({cfg.TIMEZONE}): <code>KK.OO.YYYY SS:DD</code>",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(AdCreateState.waiting_schedule_time)
async def receive_ad_schedule_time(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    cfg = get_settings()
    parsed = parse_local_datetime(message.text or "", cfg.TIMEZONE)
    if parsed is None:
        await message.answer("⚠️ Noto'g'ri format! Namuna: <code>25.12.2026 15:00</code>", parse_mode="HTML")
        return
    if parsed <= now_utc():
        await message.answer("⚠️ Kelajakdagi vaqtni kiriting.")
        return

    await state.update_data(scheduled_at_iso=parsed.isoformat())
    await state.set_state(AdCreateState.confirm)
    await message.answer(
        f"📅 Reklama <b>{format_local_dt(parsed, cfg.TIMEZONE)}</b> ga rejalashtiriladi. Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=post_schedule_confirm_kb(is_ad=True),
    )


@router.callback_query(AdCreateState.confirm, F.data == "ad:confirm_sched")
async def cb_ad_confirm_schedule(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    assert admin is not None
    d = await state.get_data()
    run_at = datetime.fromisoformat(d["scheduled_at_iso"])
    ad, _ = await PostService(session, bot).schedule_post(
        created_by=admin.telegram_id,
        post_type=PostType.AD,
        content_type=ContentType(d["content_type"]),
        run_at=run_at,
        text=d.get("text"),
        media_file_id=d.get("media_file_id"),
        buttons_json=d.get("buttons_json") or None,
    )
    await state.clear()
    await callback.answer("Rejalashtirildi")
    cfg = get_settings()
    if callback.message:
        await callback.message.answer(
            f"✅ <b>Reklama #{ad.id} rejalashtirildi!</b>\n🕒 Vaqt: <b>{format_local_dt(run_at, cfg.TIMEZONE)}</b>",
            parse_mode="HTML",
            reply_markup=ads_menu_kb(),
        )


async def _send_ads_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    *,
    page: int = 1,
    statuses: Optional[list[PostStatus]] = None,
    title: str = "📋 <b>Reklamalar ro'yxati</b>",
) -> None:
    offset = (page - 1) * PAGE_SIZE
    items, total = await PostRepository(session).list_posts(
        post_type=PostType.AD,
        statuses=statuses,
        limit=PAGE_SIZE,
        offset=offset,
    )
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    text = f"{title}\nJami: <b>{total}</b> ta"
    if not items:
        text += "\n\nHozircha reklamalar mavjud emas."
    kb = ads_list_kb(items, page=page, total_pages=total_pages)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_AD_HISTORY)
async def show_ads_history(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await _send_ads_list(message, session, page=1, title="📋 <b>Reklamalar tarixi</b>")


@router.message(F.text == BTN_AD_EDIT)
async def show_ads_edit(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await _send_ads_list(
        message,
        session,
        statuses=[PostStatus.PUBLISHED, PostStatus.SCHEDULED, PostStatus.PAUSED],
        title="✏️ <b>Tahrirlash uchun reklamani tanlang</b>",
    )


@router.message(F.text == BTN_AD_DELETE)
async def show_ads_delete(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await _send_ads_list(
        message,
        session,
        statuses=[PostStatus.PUBLISHED, PostStatus.SCHEDULED, PostStatus.PAUSED],
        title="🗑 <b>O'chirish uchun reklamani tanlang</b>",
    )


@router.message(F.text == BTN_AD_PAUSE)
async def show_ads_pause(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    await _send_ads_list(
        message,
        session,
        statuses=[PostStatus.SCHEDULED, PostStatus.PAUSED],
        title="⏸ <b>To'xtatish/Qayta yoqish uchun reklamani tanlang</b>",
    )


@router.callback_query(F.data.startswith("ad:list:"))
async def cb_ads_pagination(callback: CallbackQuery, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    page = max(1, int(callback.data.split(":")[2]))
    await _send_ads_list(callback, session, page=page)


@router.callback_query(F.data.startswith("ad:view:"))
async def cb_view_ad(callback: CallbackQuery, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    ad_id = int(callback.data.split(":")[2])
    ad = await PostRepository(session).get_by_id(ad_id)
    if not ad:
        await callback.answer("Reklama topilmadi.", show_alert=True)
        return
    cfg = get_settings()
    info = (
        f"📢 <b>Reklama #{ad.id}</b> | {STATUS_LABELS.get(ad.status, ad.status)}\n"
        f"📦 Turi: <b>{ad.content_type}</b>\n"
        f"📅 Rejalashtirilgan: {format_local_dt(ad.scheduled_at, cfg.TIMEZONE)}\n"
        f"✅ Joylangan: {format_local_dt(ad.published_at, cfg.TIMEZONE)}\n\n"
        f"<b>Matn:</b>\n{escape_html((ad.text or '(matnsiz)')[:1500])}"
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(info, parse_mode="HTML", reply_markup=ad_detail_kb(ad))


@router.callback_query(F.data.startswith("ad:edit:"))
async def cb_ad_start_edit(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    ad_id = int(callback.data.split(":")[2])
    await state.set_state(AdEditState.waiting_new_text)
    await state.update_data(edit_ad_id=ad_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"✏️ <b>Reklama #{ad_id}</b> uchun yangi matn yuboring:",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(AdEditState.waiting_new_text)
async def receive_ad_edit_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_ADS):
        return
    assert admin is not None
    if not message.text:
        await message.answer("⚠️ Yangi matn yuboring.")
        return
    ad_id = int((await state.get_data())["edit_ad_id"])
    ok, msg = await PostService(session, bot).edit_post(
        post_id=ad_id,
        editor_id=admin.telegram_id,
        new_text=message.html_text or message.text,
    )
    await state.clear()
    await message.answer(f"{'✅' if ok else '⚠️'} {escape_html(msg)}", parse_mode="HTML", reply_markup=ads_menu_kb())


@router.callback_query(F.data.startswith("ad:toggle_pause:"))
async def cb_ad_toggle_pause(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    assert admin is not None
    ad_id = int(callback.data.split(":")[2])
    ok, msg = await PostService(session, bot).pause_or_resume_ad(post_id=ad_id, actor_id=admin.telegram_id)
    await callback.answer(msg[:180], show_alert=not ok)
    ad = await PostRepository(session).get_by_id(ad_id)
    if ad and callback.message:
        await callback.message.edit_reply_markup(reply_markup=ad_detail_kb(ad))


@router.callback_query(F.data.startswith("ad:del_ask:"))
async def cb_ad_del_ask(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    ad_id = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"⚠️ <b>Reklama #{ad_id} ni o'chirishni tasdiqlaysizmi?</b>",
            parse_mode="HTML",
            reply_markup=post_delete_confirm_kb(ad_id, is_ad=True),
        )


@router.callback_query(F.data.startswith("ad:del_yes:"))
async def cb_ad_del_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_ADS):
        return
    assert admin is not None
    ad_id = int(callback.data.split(":")[2])
    ok, msg = await PostService(session, bot).delete_post(post_id=ad_id, actor_id=admin.telegram_id)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(f"{'✅' if ok else '⚠️'} {escape_html(msg)}", parse_mode="HTML")
