"""Postlarni yaratish, tahrirlash, o'chirish, rejalashtirish va qayta joylash handlerlari."""

from __future__ import annotations

import math
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.handlers.common import require_permission
from app.keyboards.common import BTN_ADMIN_POSTS, BTN_SKIP, cancel_only_kb
from app.keyboards.posts import (
    BTN_POST_DELETE,
    BTN_POST_DOC,
    BTN_POST_EDIT,
    BTN_POST_HISTORY,
    BTN_POST_NEW,
    BTN_POST_PHOTO,
    BTN_POST_REPOST,
    BTN_POST_SCHEDULED,
    BTN_POST_VIDEO,
    post_confirm_kb,
    post_delete_confirm_kb,
    post_detail_kb,
    post_repost_confirm_kb,
    post_schedule_confirm_kb,
    posts_list_kb,
    posts_menu_kb,
)
from app.models.admin import Admin
from app.models.enums import ContentType, Permission, PostStatus, PostType
from app.repositories.post_repo import PostRepository
from app.services.channel_service import ChannelService, explain_telegram_error
from app.services.post_service import PostService
from app.utils.formatting import STATUS_LABELS
from app.utils.fsm import PostCreateState, PostEditState
from app.utils.security import escape_html, parse_inline_buttons_text
from app.utils.timezone import format_local_dt, now_utc, parse_local_datetime

router = Router(name="posts_manage")
PAGE_SIZE = 8


@router.message(F.text == BTN_ADMIN_POSTS)
async def open_posts_menu(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await state.clear()
    await message.answer(
        "📝 <b>POSTLARNI BOSHQARISH</b>\n\n"
        "Kanalga matnli, rasmli, videoli yoki hujjatli post joylashingiz, "
        "mavjud postlarni tahrirlashingiz, o'chirishingiz va vaqtga rejalashtirishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=posts_menu_kb(),
    )


async def _start_post_creation(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
    content_type: ContentType,
    prompt_text: str,
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await state.clear()
    await state.set_state(PostCreateState.waiting_content)
    await state.update_data(content_type=content_type.value, post_type=PostType.POST.value)
    await message.answer(prompt_text, parse_mode="HTML", reply_markup=cancel_only_kb())


@router.message(F.text == BTN_POST_NEW)
async def start_text_post(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    await _start_post_creation(
        message,
        state,
        admin,
        ContentType.TEXT,
        "📝 <b>Yangi matnli post</b>\n\n"
        "Post matnini yuboring. HTML formatlash qo'llab-quvvatlanadi "
        "(<code>&lt;b&gt;qalin&lt;/b&gt;</code>, <code>&lt;i&gt;kursiv&lt;/i&gt;</code>, "
        "<code>&lt;a href=\"...\"&gt;havola&lt;/a&gt;</code>).",
    )


@router.message(F.text == BTN_POST_PHOTO)
async def start_photo_post(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    await _start_post_creation(
        message,
        state,
        admin,
        ContentType.PHOTO,
        "📷 <b>Yangi rasmli post</b>\n\nRasmni izoh (caption) bilan birga yuboring.",
    )


@router.message(F.text == BTN_POST_VIDEO)
async def start_video_post(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    await _start_post_creation(
        message,
        state,
        admin,
        ContentType.VIDEO,
        "🎥 <b>Yangi videoli post</b>\n\nVideoni izoh (caption) bilan birga yuboring.",
    )


@router.message(F.text == BTN_POST_DOC)
async def start_document_post(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    await _start_post_creation(
        message,
        state,
        admin,
        ContentType.DOCUMENT,
        "📄 <b>Yangi hujjatli post</b>\n\nHujjat faylini izoh (caption) bilan birga yuboring.",
    )


@router.message(PostCreateState.waiting_content)
async def receive_post_content(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        await state.clear()
        return

    data = await state.get_data()
    expected = ContentType(data["content_type"])
    text: Optional[str] = None
    media_file_id: Optional[str] = None

    if expected == ContentType.TEXT:
        if not message.text:
            await message.answer("⚠️ Iltimos, matnli xabar yuboring.")
            return
        text = message.html_text or message.text
    elif expected == ContentType.PHOTO:
        if not message.photo:
            await message.answer("⚠️ Iltimos, rasm (photo) yuboring.")
            return
        media_file_id = message.photo[-1].file_id
        text = message.html_text if message.caption else ""
    elif expected == ContentType.VIDEO:
        if not message.video:
            await message.answer("⚠️ Iltimos, video fayl yuboring.")
            return
        media_file_id = message.video.file_id
        text = message.html_text if message.caption else ""
    elif expected == ContentType.DOCUMENT:
        if not message.document:
            await message.answer("⚠️ Iltimos, hujjat (document) yuboring.")
            return
        media_file_id = message.document.file_id
        text = message.html_text if message.caption else ""

    await state.update_data(text=text, media_file_id=media_file_id)
    await state.set_state(PostCreateState.waiting_buttons)
    await message.answer(
        "🔗 <b>Inline tugmalar qo'shish (ixtiyoriy)</b>\n\n"
        "Agar post ostida tugmalar bo'lishini xohlasangiz, har bir qatorda quyidagi formatda yuboring:\n"
        "<code>Tugma matni | https://t.me/AvtoVatanparvar_testlari</code>\n\n"
        "Tugmasiz davom etish uchun <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(allow_skip=True),
    )


@router.message(PostCreateState.waiting_buttons)
async def receive_post_buttons(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        await state.clear()
        return

    buttons_json: list[dict[str, str]] = []
    if message.text and message.text.strip() != BTN_SKIP:
        buttons_json, errors = parse_inline_buttons_text(message.text)
        if errors:
            await message.answer(
                "⚠️ <b>Tugmalar formatida xatolik:</b>\n" + "\n".join(f"• {e}" for e in errors),
                parse_mode="HTML",
            )
            return

    await state.update_data(buttons_json=buttons_json)
    data = await state.get_data()

    # Oldindan ko'rish (Preview)
    channel_svc = ChannelService(bot)
    await message.answer("👁 <b>Postning oldindan ko'rinishi:</b>", parse_mode="HTML")
    try:
        await channel_svc.send_content(
            chat_id=message.chat.id,
            content_type=data["content_type"],
            text=data.get("text"),
            media_file_id=data.get("media_file_id"),
            buttons_json=buttons_json,
        )
    except Exception as exc:
        await message.answer(
            f"⚠️ <b>Postni oldindan ko'rsatishda xatolik:</b>\n{escape_html(explain_telegram_error(exc))}\n\n"
            "Matnni qaytadan yuboring.",
            parse_mode="HTML",
        )
        await state.set_state(PostCreateState.waiting_content)
        return

    await state.set_state(PostCreateState.confirm)
    await message.answer(
        "Ushbu postni kanalga joylashtirish yoki vaqtga rejalashtirishni tasdiqlang:",
        reply_markup=post_confirm_kb(is_ad=False),
    )


@router.callback_query(PostCreateState.confirm, F.data == "post:confirm_now")
async def confirm_publish_post_now(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    assert admin is not None
    data = await state.get_data()
    post_svc = PostService(session, bot)

    post, msg = await post_svc.publish_now(
        created_by=admin.telegram_id,
        post_type=PostType.POST,
        content_type=ContentType(data["content_type"]),
        text=data.get("text"),
        media_file_id=data.get("media_file_id"),
        buttons_json=data.get("buttons_json") or None,
    )
    await state.clear()
    await callback.answer()
    if callback.message:
        prefix = "✅" if post else "⚠️"
        await callback.message.answer(
            f"{prefix} {escape_html(msg)}",
            parse_mode="HTML",
            reply_markup=posts_menu_kb(),
        )


@router.callback_query(PostCreateState.confirm, F.data == "post:choose_schedule")
async def ask_post_schedule_time(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    await state.set_state(PostCreateState.waiting_schedule_time)
    await callback.answer()
    cfg = get_settings()
    if callback.message:
        await callback.message.answer(
            f"📅 <b>Postni rejalashtirish ({cfg.TIMEZONE})</b>\n\n"
            "Post chiqarish sanasi va vaqtini quyidagi formatda yuboring:\n"
            "<code>KK.OO.YYYY SS:DD</code>\n"
            "Masalan: <code>25.12.2026 18:30</code>",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(PostCreateState.waiting_schedule_time)
async def receive_post_schedule_time(
    message: Message,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    cfg = get_settings()
    parsed_utc = parse_local_datetime(message.text or "", cfg.TIMEZONE)
    if parsed_utc is None:
        await message.answer(
            "⚠️ Sana/vaqt formati noto'g'ri. Namuna: <code>25.12.2026 18:30</code>",
            parse_mode="HTML",
        )
        return
    if parsed_utc <= now_utc():
        await message.answer("⚠️ O'tib ketgan vaqtni tanlab bo'lmaydi. Kelajakdagi vaqtni kiriting.")
        return

    await state.update_data(scheduled_at_iso=parsed_utc.isoformat())
    await state.set_state(PostCreateState.confirm)
    await message.answer(
        f"📅 Post <b>{format_local_dt(parsed_utc, cfg.TIMEZONE)}</b> ({cfg.TIMEZONE}) ga rejalashtiriladi.\n"
        "Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=post_schedule_confirm_kb(is_ad=False),
    )


@router.callback_query(PostCreateState.confirm, F.data == "post:confirm_sched")
async def confirm_schedule_post(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    assert admin is not None
    from datetime import datetime

    data = await state.get_data()
    run_at = datetime.fromisoformat(data["scheduled_at_iso"])
    post_svc = PostService(session, bot)
    post, msg = await post_svc.schedule_post(
        created_by=admin.telegram_id,
        post_type=PostType.POST,
        content_type=ContentType(data["content_type"]),
        run_at=run_at,
        text=data.get("text"),
        media_file_id=data.get("media_file_id"),
        buttons_json=data.get("buttons_json") or None,
    )
    await state.clear()
    await callback.answer("Rejalashtirildi")
    cfg = get_settings()
    if callback.message:
        await callback.message.answer(
            f"✅ <b>Post #{post.id} rejalashtirildi!</b>\n"
            f"🕒 Chiqarish vaqti: <b>{format_local_dt(run_at, cfg.TIMEZONE)}</b> ({cfg.TIMEZONE})",
            parse_mode="HTML",
            reply_markup=posts_menu_kb(),
        )


async def _send_posts_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    *,
    mode: str,
    page: int = 1,
) -> None:
    repo = PostRepository(session)
    offset = (page - 1) * PAGE_SIZE
    if mode == "scheduled":
        items, total = await repo.list_posts(
            post_type=PostType.POST,
            status=PostStatus.SCHEDULED,
            limit=PAGE_SIZE,
            offset=offset,
        )
        title = "📅 <b>Rejalashtirilgan postlar</b>"
    elif mode in {"edit", "delete", "repost"}:
        items, total = await repo.list_posts(
            post_type=PostType.POST,
            statuses=[PostStatus.PUBLISHED, PostStatus.SCHEDULED],
            limit=PAGE_SIZE,
            offset=offset,
        )
        titles = {
            "edit": "✏️ <b>Tahrirlash uchun bot boshqargan postni tanlang:</b>",
            "delete": "🗑 <b>O'chirish uchun bot boshqargan postni tanlang:</b>",
            "repost": "🔁 <b>Qayta joylash uchun postni tanlang:</b>",
        }
        title = titles[mode]
    else:
        items, total = await repo.list_posts(
            post_type=PostType.POST,
            limit=PAGE_SIZE,
            offset=offset,
        )
        title = "📚 <b>Postlar tarixi</b>"

    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    text = f"{title}\nJami: <b>{total}</b> ta"
    if not items:
        text += "\n\nHozircha bu bo'limda postlar mavjud emas."

    kb = posts_list_kb(items, mode=mode, page=page, total_pages=total_pages)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_POST_SCHEDULED)
async def show_scheduled_posts(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await _send_posts_list(message, session, mode="scheduled", page=1)


@router.message(F.text == BTN_POST_HISTORY)
async def show_posts_history(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await _send_posts_list(message, session, mode="history", page=1)


@router.message(F.text == BTN_POST_EDIT)
async def show_posts_for_edit(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await _send_posts_list(message, session, mode="edit", page=1)


@router.message(F.text == BTN_POST_DELETE)
async def show_posts_for_delete(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await _send_posts_list(message, session, mode="delete", page=1)


@router.message(F.text == BTN_POST_REPOST)
async def show_posts_for_repost(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    await _send_posts_list(message, session, mode="repost", page=1)


@router.callback_query(F.data.startswith("post:list:"))
async def cb_posts_pagination(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    _, _, mode, page_str = callback.data.split(":")
    await _send_posts_list(callback, session, mode=mode, page=max(1, int(page_str)))


@router.callback_query(F.data.startswith("post:view:"))
async def cb_view_post(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    parts = callback.data.split(":")
    post_id = int(parts[2])
    post = await PostRepository(session).get_by_id(post_id)
    if not post:
        await callback.answer("Post topilmadi.", show_alert=True)
        return

    cfg = get_settings()
    status_txt = STATUS_LABELS.get(post.status, post.status)
    info = (
        f"📝 <b>Post #{post.id}</b> | {status_txt}\n"
        f"📦 Turi: <b>{post.content_type}</b>\n"
        f"🆔 Kanal xabar ID: <code>{post.channel_message_id or '—'}</code>\n"
        f"📅 Rejalashtirilgan: {format_local_dt(post.scheduled_at, cfg.TIMEZONE)}\n"
        f"✅ Joylangan: {format_local_dt(post.published_at, cfg.TIMEZONE)}\n\n"
        f"<b>Matn:</b>\n{escape_html((post.text or '(matnsiz)')[:1500])}"
    )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(info, parse_mode="HTML", reply_markup=post_detail_kb(post))


@router.callback_query(F.data.startswith("post:edit:"))
async def cb_start_edit_post(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    post_id = int(callback.data.split(":")[2])
    post = await PostRepository(session).get_by_id(post_id)
    if not post:
        await callback.answer("Post topilmadi.", show_alert=True)
        return

    await state.set_state(PostEditState.waiting_new_text)
    await state.update_data(edit_post_id=post_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"✏️ <b>Post #{post_id} ni tahrirlash</b>\n\nYangi matn (yoki media caption) yuboring:",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(),
        )


@router.message(PostEditState.waiting_new_text)
async def receive_post_edit_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_POSTS):
        return
    assert admin is not None
    if not message.text:
        await message.answer("⚠️ Iltimos, yangi matn yuboring.")
        return

    data = await state.get_data()
    post_id = int(data["edit_post_id"])
    post_svc = PostService(session, bot)
    ok, msg = await post_svc.edit_post(
        post_id=post_id,
        editor_id=admin.telegram_id,
        new_text=message.html_text or message.text,
    )
    await state.clear()
    icon = "✅" if ok else "⚠️"
    await message.answer(
        f"{icon} {escape_html(msg)}",
        parse_mode="HTML",
        reply_markup=posts_menu_kb(),
    )


@router.callback_query(F.data.startswith("post:del_ask:"))
async def cb_ask_delete_post(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    post_id = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"⚠️ <b>Post #{post_id} ni o'chirishni tasdiqlaysizmi?</b>\n\n"
            "Agar post kanalga joylangan bo'lsa, u kanaldan ham o'chiriladi.",
            parse_mode="HTML",
            reply_markup=post_delete_confirm_kb(post_id, is_ad=False),
        )


@router.callback_query(F.data.startswith("post:del_yes:"))
async def cb_confirm_delete_post(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    assert admin is not None
    post_id = int(callback.data.split(":")[2])
    ok, msg = await PostService(session, bot).delete_post(post_id=post_id, actor_id=admin.telegram_id)
    await callback.answer()
    icon = "✅" if ok else "⚠️"
    if callback.message:
        await callback.message.edit_text(f"{icon} {escape_html(msg)}", parse_mode="HTML")


@router.callback_query(F.data.startswith("post:repost_ask:"))
async def cb_ask_repost(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    post_id = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"🔁 <b>Post #{post_id} ni kanalga qayta joylashni tasdiqlaysizmi?</b>",
            parse_mode="HTML",
            reply_markup=post_repost_confirm_kb(post_id),
        )


@router.callback_query(F.data.startswith("post:repost_yes:"))
async def cb_confirm_repost(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_POSTS):
        return
    assert admin is not None
    post_id = int(callback.data.split(":")[2])
    new_post, msg = await PostService(session, bot).repost(post_id=post_id, actor_id=admin.telegram_id)
    await callback.answer()
    icon = "✅" if new_post else "⚠️"
    if callback.message:
        await callback.message.edit_text(f"{icon} {escape_html(msg)}", parse_mode="HTML")
