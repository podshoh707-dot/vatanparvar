"""Testlarni qo'shish, tahrirlash, o'chirish, tasdiqlash, qidirish va Excel import/eksport handlerlari."""

from __future__ import annotations

import io
import math
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.common import require_permission
from app.keyboards.common import BTN_ADMIN_TESTS, BTN_SKIP, cancel_only_kb, inline_nav_row
from app.keyboards.tests import (
    BTN_TEST_ADD,
    BTN_TEST_ALL,
    BTN_TEST_APPROVE,
    BTN_TEST_DELETE,
    BTN_TEST_EDIT,
    BTN_TEST_EXPORT,
    BTN_TEST_IMPORT,
    BTN_TEST_PENDING,
    BTN_TEST_SEARCH,
    BTN_TEST_TOPICS,
    correct_option_kb,
    difficulty_kb,
    excel_import_kb,
    test_create_confirm_kb,
    test_delete_confirm_kb,
    test_detail_kb,
    test_edit_fields_kb,
    tests_list_kb,
    tests_menu_kb,
)
from app.models.admin import Admin
from app.models.enums import Difficulty, Permission, PublishMode, TestStatus
from app.repositories.system_repo import SystemRepository
from app.repositories.test_repo import TestRepository
from app.services.excel_service import ExcelService
from app.services.test_service import TestService
from app.utils.formatting import format_test_card_admin
from app.utils.fsm import TestCreateState, TestEditState, TestImportState, TestSearchState
from app.utils.security import compute_question_hash, escape_html
from app.utils.timezone import now_local, now_utc

router = Router(name="tests_manage")
PAGE_SIZE = 8


@router.message(F.text == BTN_ADMIN_TESTS)
async def open_tests_menu(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await state.clear()
    await message.answer(
        "🚦 <b>TESTLARNI BOSHQARISH</b>\n\n"
        "Yangi test qo'shishingiz, Excel orqali ommaviy yuklashingiz, "
        "eksport qilishingiz, tasdiqlashingiz va kanalga chiqarishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=tests_menu_kb(),
    )


# ==================== TEST QO'SHISH WIZARD ====================


@router.message(F.text == BTN_TEST_ADD)
async def start_add_test(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await state.clear()
    await state.set_state(TestCreateState.waiting_question)
    await message.answer(
        "➕ <b>Yangi test qo'shish (1/10)</b>\n\nSavol matnini yuboring:",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(),
    )


@router.message(TestCreateState.waiting_question)
async def test_step_question(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("⚠️ Savol matni kamida 5 ta belgidan iborat bo'lishi kerak.")
        return
    await state.update_data(question_text=text)
    await state.set_state(TestCreateState.waiting_option_a)
    await message.answer("<b>(2/10) A</b> javob variantini yuboring:", parse_mode="HTML")


@router.message(TestCreateState.waiting_option_a)
async def test_step_a(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ A variant bo'sh bo'lishi mumkin emas.")
        return
    await state.update_data(option_a=text)
    await state.set_state(TestCreateState.waiting_option_b)
    await message.answer("<b>(3/10) B</b> javob variantini yuboring:", parse_mode="HTML")


@router.message(TestCreateState.waiting_option_b)
async def test_step_b(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ B variant bo'sh bo'lishi mumkin emas.")
        return
    await state.update_data(option_b=text)
    await state.set_state(TestCreateState.waiting_option_c)
    await message.answer("<b>(4/10) C</b> javob variantini yuboring:", parse_mode="HTML")


@router.message(TestCreateState.waiting_option_c)
async def test_step_c(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ C variant bo'sh bo'lishi mumkin emas.")
        return
    await state.update_data(option_c=text)
    await state.set_state(TestCreateState.waiting_option_d)
    await message.answer("<b>(5/10) D</b> javob variantini yuboring:", parse_mode="HTML")


@router.message(TestCreateState.waiting_option_d)
async def test_step_d(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ D variant bo'sh bo'lishi mumkin emas.")
        return
    await state.update_data(option_d=text)
    await state.set_state(TestCreateState.waiting_correct)
    await message.answer(
        "<b>(6/10) To'g'ri javob</b> variantini tanlang:",
        parse_mode="HTML",
        reply_markup=correct_option_kb(),
    )


@router.callback_query(TestCreateState.waiting_correct, F.data.startswith("tcreate:corr:"))
async def test_step_correct(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    corr = callback.data.split(":")[2]
    await state.update_data(correct_option=corr)
    await state.set_state(TestCreateState.waiting_explanation)
    await callback.answer(f"Tanlandi: {corr}")
    if callback.message:
        await callback.message.answer(
            "<b>(7/10) Izoh (tushuntirish)</b> matnini yuboring.\n"
            "Izohsiz davom etish uchun <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(allow_skip=True),
        )


@router.message(TestCreateState.waiting_explanation)
async def test_step_explanation(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    raw = (message.text or "").strip()
    explanation = None if (not raw or raw == BTN_SKIP) else raw
    await state.update_data(explanation=explanation)
    await state.set_state(TestCreateState.waiting_topic)
    await message.answer(
        "<b>(8/10) Test mavzusini</b> kiriting (masalan: <i>Yo'l belgilari</i>, <i>Chorrahalar</i>):",
        parse_mode="HTML",
        reply_markup=cancel_only_kb(),
    )


@router.message(TestCreateState.waiting_topic)
async def test_step_topic(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    topic = (message.text or "").strip() or "Umumiy"
    await state.update_data(topic=topic[:120])
    await state.set_state(TestCreateState.waiting_difficulty)
    await message.answer(
        "<b>(9/10) Qiyinlik darajasini</b> tanlang:",
        parse_mode="HTML",
        reply_markup=difficulty_kb(),
    )


@router.callback_query(TestCreateState.waiting_difficulty, F.data.startswith("tcreate:diff:"))
async def test_step_difficulty(callback: CallbackQuery, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    diff = callback.data.split(":")[2]
    await state.update_data(difficulty=diff)
    await state.set_state(TestCreateState.waiting_image)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "<b>(10/10) Test uchun rasm</b> yuboring (ixtiyoriy).\n"
            "Rasmsiz saqlash uchun <b>⏭ O'tkazib yuborish</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=cancel_only_kb(allow_skip=True),
        )


@router.message(TestCreateState.waiting_image)
async def test_step_image(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    image_file_id: Optional[str] = None
    if message.photo:
        image_file_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == BTN_SKIP:
        image_file_id = None
    else:
        await message.answer("⚠️ Rasm yuboring yoki ⏭ O'tkazib yuborish tugmasini bosing.")
        return

    await state.update_data(image_file_id=image_file_id)
    d = await state.get_data()
    preview = (
        "👁 <b>YANGI TEST — OLDINDAN KO'RISH</b>\n\n"
        f"❓ <b>{escape_html(d['question_text'])}</b>\n\n"
        f"A) {escape_html(d['option_a'])}\n"
        f"B) {escape_html(d['option_b'])}\n"
        f"C) {escape_html(d['option_c'])}\n"
        f"D) {escape_html(d['option_d'])}\n\n"
        f"✅ To'g'ri javob: <b>{d['correct_option']}</b>\n"
        f"💡 Izoh: {escape_html(d.get('explanation') or 'Kiritilmagan')}\n"
        f"📚 Mavzu: <b>{escape_html(d['topic'])}</b> | Qiyinlik: <b>{d['difficulty']}</b>\n"
        f"🖼 Rasm: {'Bor' if image_file_id else 'Yoq'}"
    )
    await state.set_state(TestCreateState.confirm)
    await message.answer(
        preview,
        parse_mode="HTML",
        reply_markup=test_create_confirm_kb(can_approve=admin.can(Permission.APPROVE_TESTS)),
    )


@router.callback_query(TestCreateState.confirm, F.data.startswith("tcreate:save:"))
async def test_confirm_save(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    mode = callback.data.split(":")[2]
    auto_approve = mode == "approved" and admin.can(Permission.APPROVE_TESTS)
    d = await state.get_data()

    svc = TestService(session, bot)
    q, msg = await svc.create_test(
        question_text=d["question_text"],
        option_a=d["option_a"],
        option_b=d["option_b"],
        option_c=d["option_c"],
        option_d=d["option_d"],
        correct_option=d["correct_option"],
        explanation=d.get("explanation"),
        topic=d["topic"],
        difficulty=Difficulty(d["difficulty"]),
        image_file_id=d.get("image_file_id"),
        created_by=admin.telegram_id,
        auto_approve=auto_approve,
    )
    await state.clear()
    await callback.answer()
    icon = "✅" if q else "⚠️"
    if callback.message:
        await callback.message.answer(
            f"{icon} {escape_html(msg)}",
            parse_mode="HTML",
            reply_markup=tests_menu_kb(),
        )


# ==================== RO'YXATLAR, QIDIRISH, MAVZULAR ====================


async def _send_tests_list(
    target: Message | CallbackQuery,
    session: AsyncSession,
    *,
    scope: str = "all",
    page: int = 1,
    topic: Optional[str] = None,
    search_query: Optional[str] = None,
) -> None:
    repo = TestRepository(session)
    offset = (page - 1) * PAGE_SIZE
    status_filter = TestStatus.PENDING if scope == "pending" else None

    items, total = await repo.list_questions(
        status=status_filter,
        topic=topic,
        search_query=search_query,
        limit=PAGE_SIZE,
        offset=offset,
    )
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    header_map = {
        "all": "📋 <b>Barcha testlar</b>",
        "pending": "⏳ <b>Tasdiqlanmagan testlar</b>",
        "edit": "✏️ <b>Tahrirlash uchun testni tanlang</b>",
        "delete": "🗑 <b>O'chirish uchun testni tanlang</b>",
    }
    title = header_map.get(scope, "📋 <b>Testlar ro'yxati</b>")
    if topic:
        title = f"📚 <b>Mavzu: {escape_html(topic)}</b>"
    elif search_query:
        title = f"🔎 <b>Qidiruv: '{escape_html(search_query)}'</b>"

    text = f"{title}\nTopildi: <b>{total}</b> ta test"
    if not items:
        text += "\n\nBu bo'limda hozircha test topilmadi."

    kb = tests_list_kb(items, scope=scope, page=page, total_pages=total_pages)
    if isinstance(target, CallbackQuery) and target.message:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_TEST_ALL)
async def show_all_tests(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await _send_tests_list(message, session, scope="all", page=1)


@router.message(F.text.in_({BTN_TEST_PENDING, BTN_TEST_APPROVE}))
async def show_pending_tests(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await _send_tests_list(message, session, scope="pending", page=1)


@router.message(F.text == BTN_TEST_EDIT)
async def show_tests_for_edit(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await _send_tests_list(message, session, scope="edit", page=1)


@router.message(F.text == BTN_TEST_DELETE)
async def show_tests_for_delete(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await _send_tests_list(message, session, scope="delete", page=1)


@router.callback_query(F.data.startswith("test:list:"))
async def cb_tests_pagination(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    _, _, scope, page_str = callback.data.split(":")
    await _send_tests_list(callback, session, scope=scope, page=max(1, int(page_str)))


@router.message(F.text == BTN_TEST_SEARCH)
async def start_search_tests(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await state.set_state(TestSearchState.waiting_query)
    await message.answer(
        "🔎 Qidirish uchun savol, javob yoki mavzudan kalit so'z kiriting:",
        reply_markup=cancel_only_kb(),
    )


@router.message(TestSearchState.waiting_query)
async def handle_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    query = (message.text or "").strip()
    await state.clear()
    await _send_tests_list(message, session, scope="all", page=1, search_query=query)


@router.message(F.text == BTN_TEST_TOPICS)
async def show_admin_topics(message: Message, session: AsyncSession, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    topics = await TestRepository(session).list_topics(approved_only=False)
    if not topics:
        await message.answer("📚 Hali mavzular mavjud emas. Avval test qo'shing.", reply_markup=tests_menu_kb())
        return
    rows = [
        [InlineKeyboardButton(text=f"📚 {topic} ({cnt} ta)", callback_data=f"test:topic_idx:{idx}")]
        for idx, (topic, cnt) in enumerate(topics)
    ]
    rows.append(inline_nav_row("nav:tests_menu"))
    await message.answer(
        "📚 <b>Mavzular bo'yicha saralash</b>\nKerakli mavzuni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("test:topic_idx:"))
async def cb_admin_topic_filter(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    idx = int(callback.data.split(":")[2])
    topics = await TestRepository(session).list_topics(approved_only=False)
    if idx < 0 or idx >= len(topics):
        await callback.answer("Mavzu topilmadi.", show_alert=True)
        return
    topic_name = topics[idx][0]
    await _send_tests_list(callback, session, scope="all", page=1, topic=topic_name)


# ==================== TEST KO'RISH, TASDIQLASH, TAHRIRLASH, O'CHIRISH, CHIQARISH ====================


@router.callback_query(F.data.startswith("test:view:"))
async def cb_view_test(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    qid = int(callback.data.split(":")[2])
    q = await TestRepository(session).get_by_id(qid)
    if not q:
        await callback.answer("Test topilmadi.", show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            format_test_card_admin(q),
            parse_mode="HTML",
            reply_markup=test_detail_kb(q, can_approve=admin.can(Permission.APPROVE_TESTS)),
        )


@router.callback_query(F.data.startswith("test:approve:"))
async def cb_approve_test(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.APPROVE_TESTS):
        return
    assert admin is not None
    qid = int(callback.data.split(":")[2])
    ok, msg = await TestService(session, bot).approve_test(qid, admin.telegram_id)
    await callback.answer(msg[:180], show_alert=not ok)
    q = await TestRepository(session).get_by_id(qid)
    if q and callback.message:
        await callback.message.edit_text(
            format_test_card_admin(q),
            parse_mode="HTML",
            reply_markup=test_detail_kb(q, can_approve=True),
        )


@router.callback_query(F.data.startswith("test:pub:"))
async def cb_publish_test_direct(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    parts = callback.data.split(":")
    qid = int(parts[2])
    mode = PublishMode(parts[3])
    q = await TestRepository(session).get_by_id(qid)
    if not q:
        await callback.answer("Test topilmadi.", show_alert=True)
        return

    pub, msg = await TestService(session, bot).publish_test_to_channel(
        question=q,
        mode=mode,
        published_by=admin.telegram_id,
    )
    await callback.answer()
    icon = "✅" if pub else "⚠️"
    if callback.message:
        await callback.message.answer(f"{icon} {escape_html(msg)}", parse_mode="HTML")


@router.callback_query(F.data.startswith("test:edit:"))
async def cb_edit_test_menu(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    qid = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"✏️ <b>Test #{qid}</b> — qaysi maydonni tahrirlaysiz?",
            parse_mode="HTML",
            reply_markup=test_edit_fields_kb(qid),
        )


@router.callback_query(F.data.startswith("tedit:"))
async def cb_choose_test_edit_field(
    callback: CallbackQuery,
    state: FSMContext,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    _, qid_str, field_name = callback.data.split(":")
    await state.set_state(TestEditState.waiting_value)
    await state.update_data(edit_test_id=int(qid_str), edit_field=field_name)
    await callback.answer()
    hints = {
        "question_text": "Yangi savol matnini yuboring:",
        "option_a": "Yangi A javob matnini yuboring:",
        "option_b": "Yangi B javob matnini yuboring:",
        "option_c": "Yangi C javob matnini yuboring:",
        "option_d": "Yangi D javob matnini yuboring:",
        "correct_option": "Yangi to'g'ri javob harfini kiriting (A, B, C yoki D):",
        "explanation": "Yangi izoh matnini yuboring:",
        "topic": "Yangi mavzu nomini yuboring:",
        "difficulty": "Yangi qiyinlik darajasini yuboring (easy, medium yoki hard):",
        "image_file_id": "Yangi rasm yuboring (rasmni o'chirish uchun 'o'chirish' deb yozing):",
    }
    if callback.message:
        await callback.message.answer(
            f"✏️ {hints.get(field_name, 'Yangi qiymatni yuboring:')}",
            reply_markup=cancel_only_kb(),
        )


@router.message(TestEditState.waiting_value)
async def receive_test_edit_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    data = await state.get_data()
    qid = int(data["edit_test_id"])
    field_name = data["edit_field"]

    repo = TestRepository(session)
    q = await repo.get_by_id(qid)
    if not q:
        await state.clear()
        await message.answer("⚠️ Test topilmadi.", reply_markup=tests_menu_kb())
        return

    if field_name == "image_file_id":
        if message.photo:
            q.image_file_id = message.photo[-1].file_id
        elif (message.text or "").strip().lower() in {"o'chirish", "ochirish", "delete", "-"}:
            q.image_file_id = None
        else:
            await message.answer("⚠️ Rasm yuboring yoki 'o'chirish' deb yozing.")
            return
    else:
        val = (message.text or "").strip()
        if not val:
            await message.answer("⚠️ Bo'sh qiymat kiritish mumkin emas.")
            return
        if field_name == "correct_option":
            val = val.upper()
            if val not in {"A", "B", "C", "D"}:
                await message.answer("⚠️ Faqat A, B, C yoki D kiriting.")
                return
        elif field_name == "difficulty":
            val = val.lower()
            if val not in {"easy", "medium", "hard"}:
                await message.answer("⚠️ Faqat easy, medium yoki hard kiriting.")
                return
        setattr(q, field_name, val)

    # Hash yangilash va dublikat tekshirish
    new_hash = compute_question_hash(q.question_text, q.option_a, q.option_b, q.option_c, q.option_d)
    if new_hash != q.content_hash and await repo.exists_by_hash(new_hash):
        await message.answer("⚠️ Bunday mazmundagi test bazada allaqachon mavjud!")
        return
    q.content_hash = new_hash
    q.updated_at = now_utc()
    await session.flush()

    await SystemRepository(session).log_activity(
        admin_telegram_id=admin.telegram_id,
        action="test_edited",
        target_type="test_question",
        target_id=str(q.id),
        details={"field": field_name},
    )
    await state.clear()
    await message.answer(
        f"✅ <b>Test #{q.id} yangilandi!</b>\n\n{format_test_card_admin(q)}",
        parse_mode="HTML",
        reply_markup=tests_menu_kb(),
    )


@router.callback_query(F.data.startswith("test:del_ask:"))
async def cb_ask_delete_test(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    qid = int(callback.data.split(":")[2])
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"⚠️ <b>Test #{qid} ni butunlay o'chirishni tasdiqlaysizmi?</b>",
            parse_mode="HTML",
            reply_markup=test_delete_confirm_kb(qid),
        )


@router.callback_query(F.data.startswith("test:del_yes:"))
async def cb_confirm_delete_test(
    callback: CallbackQuery,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    qid = int(callback.data.split(":")[2])
    ok = await TestRepository(session).delete_question(qid)
    if ok:
        await SystemRepository(session).log_activity(
            admin_telegram_id=admin.telegram_id,
            action="test_deleted",
            target_type="test_question",
            target_id=str(qid),
        )
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            f"✅ Test #{qid} o'chirildi." if ok else "⚠️ Test topilmadi."
        )


# ==================== EXCEL IMPORT VA EKSPORT ====================


@router.message(F.text == BTN_TEST_IMPORT)
async def start_excel_import(message: Message, state: FSMContext, admin: Optional[Admin]) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    await state.set_state(TestImportState.waiting_excel_file)
    await message.answer(
        "📥 <b>Excel (.xlsx) orqali testlarni import qilish</b>\n\n"
        "Faylda quyidagi ustunlar bo'lishi shart:\n"
        "<code>savol | a | b | c | d | togri_javob</code>\n"
        "Ixtiyoriy ustunlar: <code>izoh | mavzu | qiyinlik</code>\n\n"
        "Endi <b>.xlsx</b> faylni yuboring (yoki avval namuna shablonni yuklab oling):",
        parse_mode="HTML",
        reply_markup=excel_import_kb(),
    )


@router.callback_query(F.data == "test:excel_template")
async def cb_send_excel_template(callback: CallbackQuery, admin: Optional[Admin]) -> None:
    if not await require_permission(callback, admin, Permission.MANAGE_TESTS):
        return
    data = ExcelService.build_template_bytes()
    await callback.answer("Shablon yuborilmoqda...")
    if callback.message:
        await callback.message.answer_document(
            document=BufferedInputFile(data, filename="avtovatanparvar_test_shablon.xlsx"),
            caption="📄 Namuna Excel shabloni. Ustun nomlarini o'zgartirmasdan to'ldiring.",
        )


@router.message(TestImportState.waiting_excel_file)
async def receive_excel_file(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    if not message.document:
        await message.answer("⚠️ Iltimos, .xlsx formatdagi hujjat fayl yuboring.")
        return

    fname = (message.document.file_name or "").lower()
    if not fname.endswith(".xlsx"):
        await message.answer("❌ Faqat <b>.xlsx</b> formatidagi Excel fayllar qabul qilinadi!", parse_mode="HTML")
        return

    buf = io.BytesIO()
    await bot.download(message.document, destination=buf)
    raw_bytes = buf.getvalue()

    excel_svc = ExcelService(session)
    report = await excel_svc.import_tests_from_bytes(
        raw_bytes,
        created_by=admin.telegram_id,
        auto_approve=False,
    )
    await state.clear()

    lines = [
        "📊 <b>EXCEL IMPORT NATIJASI</b>",
        "",
        f"📄 Jami ko'rilgan qatorlar: <b>{report.total_rows}</b>",
        f"✅ Muvaffaqiyatli qo'shildi: <b>{report.imported}</b> (tasdiqlash kutilmoqda)",
        f"🔁 Takroriy (o'tkazib yuborildi): <b>{report.duplicates}</b>",
        f"❌ Xatolikli qatorlar: <b>{len(report.errors)}</b>",
    ]
    if report.errors:
        lines.append("\n<b>Xatolar ro'yxati (dastlabki 15 tasi):</b>")
        for err in report.errors[:15]:
            lines.append(f"• {escape_html(err)}")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=tests_menu_kb(),
    )


@router.message(F.text == BTN_TEST_EXPORT)
async def handle_excel_export(
    message: Message,
    session: AsyncSession,
    admin: Optional[Admin],
) -> None:
    if not await require_permission(message, admin, Permission.MANAGE_TESTS):
        return
    assert admin is not None
    excel_svc = ExcelService(session)
    file_bytes, count = await excel_svc.export_tests_bytes()
    ts = now_local().strftime("%Y%m%d_%H%M")
    filename = f"avtovatanparvar_testlar_{ts}.xlsx"

    await SystemRepository(session).log_activity(
        admin_telegram_id=admin.telegram_id,
        action="tests_excel_exported",
        target_type="test_question",
        details={"count": count},
    )
    await message.answer_document(
        document=BufferedInputFile(file_bytes, filename=filename),
        caption=f"📤 Jami <b>{count}</b> ta test Excel faylga eksport qilindi.",
        parse_mode="HTML",
        reply_markup=tests_menu_kb(),
    )
