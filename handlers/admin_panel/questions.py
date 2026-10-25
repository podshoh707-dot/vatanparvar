import os
import json
from aiogram import Router, types, F, Bot
from utils.permissions import check_permission, is_superadmin
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from database import async_session, Question
from sqlalchemy import select, delete, func, or_
from config import BASE_DIR, ADMIN_IDS

questions_router = Router()


class QuestionStates(StatesGroup):
    searching_query  = State()
    adding_text      = State()
    adding_option_a  = State()
    adding_option_b  = State()
    adding_option_c  = State()
    adding_option_d  = State()
    adding_correct   = State()
    adding_image     = State()
    adding_explain   = State()
    editing_field    = State()
    editing_value    = State()
    sending_channel  = State()


def back_kb(cb: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=cb)]
    ])


async def auto_sync_questions():
    """Savollar bazasini JSON fayllar bilan avtomatik sinxronlashtirish"""
    try:
        from export_questions import export
        await export()
    except Exception as e:
        print(f"Auto-sync questions error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. SAVOLLAR RO'YXATI (PAGINATION)
# ══════════════════════════════════════════════════════════════════════════════
@questions_router.callback_query(F.data.startswith("admin_tests"))
async def admin_questions_list(callback: types.CallbackQuery, state: FSMContext = None):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    if state:
        await state.clear()

    data_parts = callback.data.split("_")
    page = 1
    if len(data_parts) > 2:
        try:
            page = int(data_parts[2])
        except ValueError:
            page = 1

    per_page = 15
    offset = (page - 1) * per_page

    async with async_session() as session:
        total_result = await session.execute(select(func.count()).select_from(Question))
        total = total_result.scalar() or 0

        result = await session.execute(
            select(Question).order_by(Question.id.asc()).offset(offset).limit(per_page)
        )
        questions = result.scalars().all()

    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    buttons = [
        [
            InlineKeyboardButton(text="🔍 Qidirish (ID / Matn)", callback_data="q_search_start"),
            InlineKeyboardButton(text="🎫 Biletlar (1-81)", callback_data="q_bilets_1")
        ],
        [
            InlineKeyboardButton(text="➕ Yangi savol qo'shish", callback_data="q_add")
        ]
    ]

    for q in questions:
        cat_badge = f"[{q.category}] " if q.category else ""
        short_text = q.text[:30] + "..." if len(q.text) > 30 else q.text
        has_img = "🖼 " if q.image_url else "📄 "
        buttons.append([
            InlineKeyboardButton(text=f"{has_img}#{q.id} {cat_badge}{short_text}", callback_data=f"q_detail_{q.id}")
        ])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_tests_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_tests_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="admin_back_main")
    ])

    start_num = offset + 1 if total > 0 else 0
    end_num = min(offset + per_page, total)

    text = (
        "🗃 <b>SAVOLLAR BAZASI BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Jami rasmiy savollar: <b>{total} ta</b>\n"
        f"📑 Sahifa: <b>{page}/{total_pages}</b> (Savollar: {start_num}–{end_num})\n\n"
        "<i>Qidirish yoki biletlar bo'yicha saralash uchun yuqoridagi tugmalardan foydalaning:</i>"
    )

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# 2. QIDIRISH (ID YOKI MATN BO'YICHA)
# ══════════════════════════════════════════════════════════════════════════════
@questions_router.callback_query(F.data == "q_search_start")
async def q_search_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(QuestionStates.searching_query)
    text = (
        "🔍 <b>SAVOLLARNI QIDIRISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Qidirmoqchi bo'lgan savol ma'lumotini kiriting:\n\n"
        "🔢 <b>ID raqami</b> (masalan: <code>72</code>)\n"
        "✍️ Yoki <b>kalit so'z</b> (masalan: <i>svetofor, chorraha, quvib o'tish</i>)\n\n"
        "Bekor qilish: /cancel"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Savollar ro'yxatiga", callback_data="admin_tests")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@questions_router.message(QuestionStates.searching_query)
async def q_search_process(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return

    query = message.text.strip() if message.text else ""
    if query == "/cancel":
        await state.clear()
        await message.answer("Qidiruv bekor qilindi. /admin")
        return

    # 1. Agar toza son bo'lsa -> ID bo'yicha to'g'ridan-to'g'ri ochish
    if query.isdigit():
        qid = int(query)
        async with async_session() as session:
            result = await session.execute(select(Question).where(Question.id == qid))
            q = result.scalars().first()
        if q:
            await state.clear()
            kb = await get_question_detail_kb(q)
            text = format_question_detail_text(q)
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
            return
        else:
            await message.answer(f"❌ #{qid} raqamli savol bazada topilmadi.\nQaytadan kiriting yoki /cancel bosing:")
            return

    # 2. Matn bo'yicha qidirish
    async with async_session() as session:
        result = await session.execute(
            select(Question).where(
                or_(
                    Question.text.ilike(f"%{query}%"),
                    Question.explanation.ilike(f"%{query}%")
                )
            ).order_by(Question.id.asc()).limit(15)
        )
        matches = result.scalars().all()

    if not matches:
        await message.answer(
            f"❌ «<b>{query}</b>» so'zi bo'yicha savol topilmadi.\nBoshqa so'z kiriting yoki /cancel bosing:",
            parse_mode="HTML"
        )
        return

    await state.clear()
    buttons = []
    for q in matches:
        cat_badge = f"[{q.category}] " if q.category else ""
        short = q.text[:35] + "..." if len(q.text) > 35 else q.text
        has_img = "🖼 " if q.image_url else "📄 "
        buttons.append([
            InlineKeyboardButton(text=f"{has_img}#{q.id} {cat_badge}{short}", callback_data=f"q_detail_{q.id}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="q_search_start"),
        InlineKeyboardButton(text="🔙 Savollar ro'yxatiga", callback_data="admin_tests")
    ])

    await message.answer(
        f"🔍 «<b>{query}</b>» so'rovi bo'yicha <b>{len(matches)} ta</b> savol topildi:\n\nKeraklisini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. BILETLAR BO'YICHA SARALASH (1-81)
# ══════════════════════════════════════════════════════════════════════════════
@questions_router.callback_query(F.data.startswith("q_bilets_"))
async def admin_bilet_list(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    page = int(callback.data.split("_")[2])
    per_page = 20
    total_bilets = 81
    total_pages = (total_bilets + per_page - 1) // per_page
    page = max(1, min(page, total_pages))

    start_bilet = (page - 1) * per_page + 1
    end_bilet = min(page * per_page, total_bilets)

    buttons = []
    row = []
    for b in range(start_bilet, end_bilet + 1):
        row.append(InlineKeyboardButton(text=f"🎫 {b}-Bilet", callback_data=f"q_bilet_{b}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"q_bilets_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"q_bilets_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="🔙 Savollar ro'yxatiga", callback_data="admin_tests"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="admin_back_main")
    ])

    text = (
        "🎫 <b>RASMIY BILETLAR BO'YICHA SARALASH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Bazada jami <b>81 ta rasmiy bilet</b> mavjud (har birida 10 tadan savol).\n"
        f"Ko'rsatilmoqda: <b>{start_bilet}–{end_bilet}</b> biletlar\n\n"
        "<i>Kerakli biletni tanlang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@questions_router.callback_query(F.data.startswith("q_bilet_"))
async def admin_bilet_detail(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    bilet_num = int(callback.data.split("_")[2])

    async with async_session() as session:
        # 1. Avval category bo'yicha qidiramiz
        result = await session.execute(
            select(Question).where(Question.category == f"{bilet_num}-Bilet").order_by(Question.id.asc())
        )
        questions = result.scalars().all()

        # 2. Agar category bilan topilmasa, ID offseti bo'yicha olamiz
        if not questions:
            offset = (bilet_num - 1) * 10
            result = await session.execute(
                select(Question).order_by(Question.id.asc()).offset(offset).limit(10)
            )
            questions = result.scalars().all()

    buttons = []
    for i, q in enumerate(questions, 1):
        short = q.text[:35] + "..." if len(q.text) > 35 else q.text
        has_img = "🖼 " if q.image_url else "📄 "
        buttons.append([
            InlineKeyboardButton(text=f"{has_img}#{q.id} ({i}-savol) {short}", callback_data=f"q_detail_{q.id}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Biletlar ro'yxatiga", callback_data="q_bilets_1"),
        InlineKeyboardButton(text="🗃 Barcha savollar", callback_data="admin_tests")
    ])

    text = (
        f"🎫 <b>{bilet_num}-BILET SAVOLLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Ushbu biletda <b>{len(questions)} ta</b> rasmiy savol mavjud.\n\n"
        "<i>Tafsilotini ko'rish yoki tahrirlash uchun savolni tanlang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# 4. SAVOL TAFSILOTI VA TAHRIRLASH
# ══════════════════════════════════════════════════════════════════════════════
def format_question_detail_text(q: Question) -> str:
    img_status = "🖼 Mavjud" if q.image_url else "📄 Yo'q (Nazariy savol)"
    text = (
        f"📋 <b>SAVOL #{q.id}</b> | 🎫 <i>{q.category or 'Umumiy'}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ <b>Savol matni:</b>\n{q.text}\n\n"
        f"<b>Variantlar:</b>\n"
        f"{'✅' if q.correct_option == 'A' else '⚪️'} <b>A)</b> {q.option_a}\n"
        f"{'✅' if q.correct_option == 'B' else '⚪️'} <b>B)</b> {q.option_b}\n"
    )
    if q.option_c:
        text += f"{'✅' if q.correct_option == 'C' else '⚪️'} <b>C)</b> {q.option_c}\n"
    if q.option_d:
        text += f"{'✅' if q.correct_option == 'D' else '⚪️'} <b>D)</b> {q.option_d}\n"

    text += f"\n🎯 <b>To'g'ri javob:</b> {q.correct_option}\n"
    text += f"🖼 <b>Rasm holati:</b> {img_status}\n"
    if q.explanation:
        text += f"📖 <b>Izoh / Qoida bandi:</b> <i>{q.explanation}</i>\n"
    return text


async def get_question_detail_kb(q: Question) -> InlineKeyboardMarkup:
    qid = q.id
    buttons = [
        [InlineKeyboardButton(text="📢 Kanalga test qilib yuborish", callback_data=f"q_send_{qid}")]
    ]

    # Rasm boshqaruvi
    if q.image_url:
        buttons.append([
            InlineKeyboardButton(text="🖼 Rasmni ko'rish", callback_data=f"q_preview_{qid}"),
            InlineKeyboardButton(text="🗑 Rasmni olib tashlash", callback_data=f"q_rmimg_{qid}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🖼 Rasm biriktirish", callback_data=f"q_edit_{qid}_image")
        ])

    buttons.append([
        InlineKeyboardButton(text="✏️ Savol matnini tahrirlash", callback_data=f"q_edit_{qid}_text")
    ])
    buttons.append([
        InlineKeyboardButton(text="✏️ A variant", callback_data=f"q_edit_{qid}_a"),
        InlineKeyboardButton(text="✏️ B variant", callback_data=f"q_edit_{qid}_b")
    ])
    buttons.append([
        InlineKeyboardButton(text="✏️ C variant", callback_data=f"q_edit_{qid}_c"),
        InlineKeyboardButton(text="✏️ D variant", callback_data=f"q_edit_{qid}_d")
    ])
    buttons.append([
        InlineKeyboardButton(text="🎯 To'g'ri javobni o'zgartirish", callback_data=f"q_edit_{qid}_correct"),
        InlineKeyboardButton(text="📖 Izohni tahrirlash", callback_data=f"q_edit_{qid}_explain")
    ])
    buttons.append([
        InlineKeyboardButton(text="🗑 Savolni butunlay o'chirish", callback_data=f"q_del_{qid}")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Savollar ro'yxatiga", callback_data="admin_tests")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@questions_router.callback_query(F.data.startswith("q_detail_"))
async def admin_question_detail(callback: types.CallbackQuery, state: FSMContext = None):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    if state:
        await state.clear()

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()

    if not q:
        await callback.answer("Savol topilmadi.", show_alert=True)
        return

    kb = await get_question_detail_kb(q)
    text = format_question_detail_text(q)

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── Rasmni ko'rish (Preview) ────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_preview_"))
async def admin_question_preview_image(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()

    if not q or not q.image_url:
        await callback.answer("Bu savolda rasm mavjud emas!", show_alert=True)
        return

    photo_obj = None
    if str(q.image_url).startswith("http"):
        photo_obj = q.image_url
    else:
        # Mahalliy fayl
        rel_path = str(q.image_url).replace('\\', '/')
        if rel_path.startswith('/'):
            rel_path = rel_path[1:]
        abs_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(abs_path):
            abs_path = os.path.join(BASE_DIR, "images", os.path.basename(rel_path))
        if os.path.exists(abs_path):
            photo_obj = FSInputFile(abs_path)

    if not photo_obj:
        await callback.answer(f"Rasm fayli topilmadi: {q.image_url}", show_alert=True)
        return

    await callback.answer("Rasm yuborilmoqda...")
    await callback.message.bot.send_photo(
        chat_id=callback.from_user.id,
        photo=photo_obj,
        caption=f"🖼 <b>#{q.id}-savol rasmi</b>\n\n/admin - panelga qaytish",
        parse_mode="HTML"
    )


# ── Rasmni olib tashlash ────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_rmimg_"))
async def admin_question_remove_image(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()
        if q:
            q.image_url = None
            await session.commit()

    await auto_sync_questions()
    await callback.answer("✅ Rasm olib tashlandi!", show_alert=True)
    await admin_question_detail(callback)


# ── Kanalga yuborish ────────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_send_"))
async def q_send_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    qid = int(callback.data.split("_")[2])
    await state.update_data(send_qid=qid)
    await state.set_state(QuestionStates.sending_channel)
    await callback.message.edit_text(
        "📢 <b>KANALGA TEST YUBORISH</b>\n\n"
        "Qaysi kanalga yubormoqchisiz? Kanal usernamesini @ bilan yozing (masalan: <code>@avtomaktab_uz</code>)\n\n"
        "<i>Eslatma: Bot ushbu kanalda administrator bo'lishi shart!</i>\n\n"
        "Bekor qilish: /cancel",
        reply_markup=back_kb(f"q_detail_{qid}"),
        parse_mode="HTML"
    )
    await callback.answer()


@questions_router.message(QuestionStates.sending_channel)
async def q_send_do(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return

    if message.text and message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    channel = message.text.strip()
    if not channel.startswith("@"):
        await message.answer("❌ Kanal usernamesi @ belgisi bilan boshlanishi kerak (masalan: @avtomaktab_uz)")
        return

    data = await state.get_data()
    qid = data.get("send_qid")

    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()

    if not q:
        await message.answer("Savol topilmadi.")
        await state.clear()
        return

    text = f"❓ <b>YHQ TESTI #{q.id}</b>\n\n{q.text}"
    buttons = [
        [InlineKeyboardButton(text=f"A) {q.option_a}", callback_data=f"ch_ans_{qid}_A")],
        [InlineKeyboardButton(text=f"B) {q.option_b}", callback_data=f"ch_ans_{qid}_B")]
    ]
    if q.option_c:
        buttons.append([InlineKeyboardButton(text=f"C) {q.option_c}", callback_data=f"ch_ans_{qid}_C")])
    if q.option_d:
        buttons.append([InlineKeyboardButton(text=f"D) {q.option_d}", callback_data=f"ch_ans_{qid}_D")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        photo_obj = None
        if q.image_url:
            if str(q.image_url).startswith("http"):
                photo_obj = q.image_url
            else:
                rel_path = str(q.image_url).replace('\\', '/')
                if rel_path.startswith('/'): rel_path = rel_path[1:]
                abs_path = os.path.join(BASE_DIR, rel_path)
                if not os.path.exists(abs_path):
                    abs_path = os.path.join(BASE_DIR, "images", os.path.basename(rel_path))
                if os.path.exists(abs_path):
                    photo_obj = FSInputFile(abs_path)

        if photo_obj:
            await message.bot.send_photo(chat_id=channel, photo=photo_obj, caption=text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.bot.send_message(chat_id=channel, text=text, reply_markup=keyboard, parse_mode="HTML")

        await message.answer(f"✅ Savol #{qid} {channel} kanaliga muvaffaqiyatli yuborildi!\n\n/admin - panelga qaytish")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi. Bot kanalda admin emasmi yoki kanal xatomi?\n\nXato: {str(e)}")

    await state.clear()


# ── Savol maydonlarini tahrirlash ──────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_edit_"))
async def admin_question_edit_field(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split("_")
    qid   = int(parts[2])
    field = parts[3]
    field_names = {
        "text": "Savol matni",
        "a": "A variant matni",
        "b": "B variant matni",
        "c": "C variant matni (agar kerak bo'lmasa 'yoq' deb yozing)",
        "d": "D variant matni (agar kerak bo'lmasa 'yoq' deb yozing)",
        "correct": "To'g'ri javob harfi (faqat A, B, C yoki D)",
        "image": "Yangi rasm (rasm biriktiring yoki uning URL manzilini yuboring)",
        "explain": "Tushuntirish / Qoida bandi (agar kerak bo'lmasa 'yoq' deb yozing)"
    }
    await state.update_data(qid=qid, field=field)
    await state.set_state(QuestionStates.editing_value)

    await callback.message.edit_text(
        f"✏️ <b>#{qid}-SAVOLNI TAHRIRLASH</b>\n\n"
        f"<b>{field_names.get(field, field)}</b> uchun yangi qiymatni kiriting:\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=back_kb(f"q_detail_{qid}"),
        parse_mode="HTML"
    )
    await callback.answer()


@questions_router.message(QuestionStates.editing_value)
async def admin_question_save_edit(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return

    if message.text and message.text == "/cancel":
        data = await state.get_data()
        qid = data.get("qid")
        await state.clear()
        await message.answer(f"Tahrirlash bekor qilindi. Savol: /admin")
        return

    data  = await state.get_data()
    qid   = data["qid"]
    field = data["field"]
    value = message.text.strip() if message.text else ""

    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()
        if not q:
            await state.clear()
            await message.answer("Savol topilmadi.")
            return

        if field == "text":
            if not value:
                await message.answer("❌ Savol matni bo'sh bo'lishi mumkin emas!")
                return
            q.text = value
        elif field == "a":
            if not value:
                await message.answer("❌ A variant bo'sh bo'lishi mumkin emas!")
                return
            q.option_a = value
        elif field == "b":
            if not value:
                await message.answer("❌ B variant bo'sh bo'lishi mumkin emas!")
                return
            q.option_b = value
        elif field == "c":
            q.option_c = None if value.lower() in ("yoq", "yo'q", "none", "-") else value
        elif field == "d":
            q.option_d = None if value.lower() in ("yoq", "yo'q", "none", "-") else value
        elif field == "correct":
            val_upper = value.upper()
            if val_upper in ("A", "B", "C", "D"):
                q.correct_option = val_upper
            else:
                await message.answer("❌ Faqat A, B, C yoki D harfini yozing!")
                return
        elif field == "image":
            if message.photo:
                q.image_url = message.photo[-1].file_id
            elif value.startswith("http") or value.startswith("images/"):
                q.image_url = value
            elif value.lower() in ("yoq", "yo'q", "none", "o'chir"):
                q.image_url = None
            else:
                await message.answer("❌ Rasm yuboring yoki rasm URL manzilini kiriting (olib tashlash uchun 'yoq' deb yozing)!")
                return
        elif field == "explain":
            q.explanation = None if value.lower() in ("yoq", "yo'q", "none", "-") else value

        await session.commit()
        updated_q = q

    await auto_sync_questions()
    await state.clear()

    kb = await get_question_detail_kb(updated_q)
    text = format_question_detail_text(updated_q)
    await message.answer(f"✅ <b>Savol #{qid} muvaffaqiyatli saqlandi!</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")


# ── Savolni o'chirish ───────────────────────────────────────────────────────
@questions_router.callback_query(F.data.startswith("q_del_"))
async def admin_question_delete_confirm(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"q_delok_{qid}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"q_detail_{qid}")
    ]])
    await callback.message.edit_text(
        f"⚠️ <b>Savol #{qid}ni butunlay o'chirishni tasdiqlaysizmi?</b>\n\n"
        "Ushbu amalni ortga qaytarib bo'lmaydi!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@questions_router.callback_query(F.data.startswith("q_delok_"))
async def admin_question_delete_ok(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    qid = int(callback.data.split("_")[2])
    async with async_session() as session:
        await session.execute(delete(Question).where(Question.id == qid))
        await session.commit()

    await auto_sync_questions()
    await callback.answer(f"🗑 Savol #{qid} o'chirildi!", show_alert=True)
    await admin_questions_list(callback)


# ══════════════════════════════════════════════════════════════════════════════
# 5. YANGI SAVOL QO'SHISH (FSM WIZARD)
# ══════════════════════════════════════════════════════════════════════════════
@questions_router.callback_query(F.data == "q_add")
async def admin_question_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(QuestionStates.adding_text)
    await callback.message.edit_text(
        "➕ <b>YANGI SAVOL QO'SHISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Savol matnini yozing:</b>\n"
        "<i>(Agar rasm biriktirmoqchi bo'lsangiz, rasmni biriktirib ostiga matnini yozib birga yuboring)</i>\n\n"
        "Bekor qilish: /cancel",
        reply_markup=back_kb("admin_tests"),
        parse_mode="HTML"
    )
    await callback.answer()


@questions_router.message(QuestionStates.adding_text)
async def q_add_text(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    if message.photo:
        text = message.caption.strip() if message.caption else ""
        image_id = message.photo[-1].file_id
    else:
        text = message.text.strip() if message.text else ""
        image_id = None

    if not text:
        await message.answer("❌ Matn kiritilmadi! Iltimos, savol matnini yozing.")
        return

    await state.update_data(text=text, image_url=image_id)
    await state.set_state(QuestionStates.adding_option_a)
    await message.answer("2️⃣ <b>A) variantini yozing:</b>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_option_a)
async def q_add_a(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    await state.update_data(option_a=message.text.strip())
    await state.set_state(QuestionStates.adding_option_b)
    await message.answer("3️⃣ <b>B) variantini yozing:</b>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_option_b)
async def q_add_b(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    await state.update_data(option_b=message.text.strip())
    await state.set_state(QuestionStates.adding_option_c)
    await message.answer("4️⃣ <b>C) variantini yozing:</b>\n<i>(agar C varianti bo'lmasa 'yoq' deb yozing)</i>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_option_c)
async def q_add_c(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    val = message.text.strip()
    await state.update_data(option_c=None if val.lower() in ("yoq", "yo'q", "none", "-") else val)
    await state.set_state(QuestionStates.adding_option_d)
    await message.answer("5️⃣ <b>D) variantini yozing:</b>\n<i>(agar D varianti bo'lmasa 'yoq' deb yozing)</i>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_option_d)
async def q_add_d(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    val = message.text.strip()
    await state.update_data(option_d=None if val.lower() in ("yoq", "yo'q", "none", "-") else val)
    await state.set_state(QuestionStates.adding_correct)
    await message.answer("6️⃣ <b>To'g'ri javob harfini yozing (A, B, C yoki D):</b>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_correct)
async def q_add_correct(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    ans = message.text.strip().upper()
    if ans not in ("A", "B", "C", "D"):
        await message.answer("❌ Faqat A, B, C yoki D harfini yozing!")
        return
    await state.update_data(correct_option=ans)
    await state.set_state(QuestionStates.adding_explain)
    await message.answer("7️⃣ <b>Izoh yoki qoida bandini yozing:</b>\n<i>(izoh bo'lmasa 'yoq' deb yozing)</i>", parse_mode="HTML")


@questions_router.message(QuestionStates.adding_explain)
async def q_add_explain(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Bekor qilindi. /admin")
        return

    exp = message.text.strip()
    data = await state.get_data()

    async with async_session() as session:
        # Eng oxirgi biletni aniqlaymiz yoki 81-Biletga qo'shamiz
        q = Question(
            text=data["text"],
            option_a=data["option_a"],
            option_b=data["option_b"],
            option_c=data.get("option_c"),
            option_d=data.get("option_d"),
            correct_option=data["correct_option"],
            image_url=data.get("image_url"),
            explanation=None if exp.lower() in ("yoq", "yo'q", "none", "-") else exp,
            category="81-Bilet",
            difficulty="o'rta"
        )
        session.add(q)
        await session.commit()
        new_id = q.id

    await auto_sync_questions()
    await state.clear()

    await message.answer(
        f"✅ <b>Savol #{new_id} muvaffaqiyatli qo'shildi va saqlandi!</b>\n\n"
        f"❓ {data['text']}\n"
        f"🎯 To'g'ri javob: <b>{data['correct_option']}</b>\n\n"
        f"/admin orqali boshqaruv markaziga qaytishingiz mumkin.",
        parse_mode="HTML"
    )
