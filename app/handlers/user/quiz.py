"""Oddiy foydalanuvchilar uchun interaktiv test ishlash handlerlari."""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common import BTN_USER_TEST
from app.keyboards.users import user_main_menu_kb, user_quiz_options_kb
from app.models.user import User
from app.repositories.test_repo import TestRepository
from app.repositories.user_repo import UserRepository
from app.utils.formatting import format_user_practice_question
from app.utils.media import resolve_media_input
from app.utils.security import escape_html

router = Router(name="user_quiz")


async def _send_quiz_question(
    target: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    q_ids: list[int] = data.get("quiz_ids", [])
    idx: int = int(data.get("quiz_idx", 0))
    correct_count: int = int(data.get("quiz_correct", 0))

    if idx >= len(q_ids):
        total = len(q_ids)
        wrong = total - correct_count
        pct = round((correct_count / total) * 100, 1) if total > 0 else 0.0
        await state.clear()
        await target.answer(
            "🏁 <b>TEST YAKUNLANDI!</b>\n\n"
            f"• Jami savollar: <b>{total}</b>\n"
            f"• ✅ To'g'ri javoblar: <b>{correct_count}</b>\n"
            f"• ❌ Noto'g'ri javoblar: <b>{wrong}</b>\n"
            f"• 🎯 Natija: <b>{pct}%</b>",
            parse_mode="HTML",
            reply_markup=user_main_menu_kb(),
        )
        return

    q = await TestRepository(session).get_by_id(q_ids[idx])
    if not q:
        await state.update_data(quiz_idx=idx + 1)
        await _send_quiz_question(target, session, state)
        return

    options_count = 2
    if q.option_c and q.option_c.strip() not in ("", "-"):
        options_count = 3
        if q.option_d and q.option_d.strip() not in ("", "-"):
            options_count = 4

    caption = format_user_practice_question(q, index=idx + 1, total=len(q_ids))
    kb = user_quiz_options_kb(q.id, options_count=options_count)

    if q.image_file_id:
        await target.answer_photo(
            photo=resolve_media_input(q.image_file_id),
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await target.answer(caption, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == BTN_USER_TEST)
async def start_random_practice(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    questions = await TestRepository(session).pick_practice_questions(limit=10)
    if not questions:
        await message.answer(
            "🚦 Hozircha tasdiqlangan test savollari mavjud emas. Tez orada qo'shiladi!",
            reply_markup=user_main_menu_kb(),
        )
        return

    await state.update_data(
        quiz_ids=[q.id for q in questions],
        quiz_idx=0,
        quiz_correct=0,
        quiz_mode="bot_practice",
    )
    await _send_quiz_question(message, session, state)


@router.callback_query(F.data.startswith("uquiz:topic_idx:"))
async def start_topic_practice(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    idx = int(callback.data.split(":")[2])
    repo = TestRepository(session)
    topics = await repo.list_topics(approved_only=True)
    if idx < 0 or idx >= len(topics):
        await callback.answer("Mavzu topilmadi.", show_alert=True)
        return

    topic_name = topics[idx][0]
    questions = await repo.pick_practice_questions(topic=topic_name, limit=10)
    if not questions:
        await callback.answer("Bu mavzuda testlar topilmadi.", show_alert=True)
        return

    await state.update_data(
        quiz_ids=[q.id for q in questions],
        quiz_idx=0,
        quiz_correct=0,
        quiz_mode="topic_practice",
    )
    await callback.answer(f"Mavzu: {topic_name}")
    if callback.message:
        await _send_quiz_question(callback.message, session, state)


@router.callback_query(F.data.startswith("uquiz:ans:"))
async def handle_user_quiz_answer(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: Optional[User],
) -> None:
    parts = callback.data.split(":")
    qid = int(parts[2])
    selected = parts[3].upper()

    data = await state.get_data()
    q_ids: list[int] = data.get("quiz_ids", [])
    idx: int = int(data.get("quiz_idx", 0))
    correct_count: int = int(data.get("quiz_correct", 0))

    if not q_ids or idx >= len(q_ids) or q_ids[idx] != qid:
        await callback.answer("Bu savol allaqachon yakunlangan.", show_alert=True)
        return

    repo = TestRepository(session)
    q = await repo.get_by_id(qid)
    if not q:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    is_correct = selected == q.correct_option.upper()
    if is_correct:
        correct_count += 1

    if db_user is not None:
        await repo.record_bot_attempt(
            user_id=db_user.id,
            question_id=q.id,
            selected_option=selected,
            is_correct=is_correct,
            mode=data.get("quiz_mode", "bot_practice"),
        )
        await UserRepository(session).increment_stats(db_user.id, is_correct=is_correct)

    await state.update_data(quiz_idx=idx + 1, quiz_correct=correct_count)

    feedback = (
        f"✅ <b>To'g'ri javob!</b> ({selected})"
        if is_correct
        else f"❌ <b>Noto'g'ri!</b> Siz tanladingiz: <b>{selected}</b> | To'g'ri javob: <b>{q.correct_option}</b>"
    )
    if q.explanation:
        feedback += f"\n💡 <b>Izoh:</b> {escape_html(q.explanation)}"

    await callback.answer("✅ To'g'ri!" if is_correct else f"❌ To'g'ri javob: {q.correct_option}")
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(feedback, parse_mode="HTML")
        await _send_quiz_question(callback.message, session, state)


@router.callback_query(F.data == "uquiz:stop")
async def stop_user_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    answered = int(data.get("quiz_idx", 0))
    correct = int(data.get("quiz_correct", 0))
    await state.clear()
    await callback.answer("Test to'xtatildi")
    if callback.message:
        await callback.message.answer(
            f"⏹ <b>Test yakunlandi.</b>\nYechilgan: <b>{answered}</b> | To'g'ri: <b>{correct}</b>",
            parse_mode="HTML",
            reply_markup=user_main_menu_kb(),
        )
