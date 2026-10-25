from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import async_session, Sign
from sqlalchemy import select
import os
from config import BASE_DIR

signs_router = Router()

class SignStates(StatesGroup):
    searching = State()

SIGNS_PER_PAGE = 8

CAT_LABELS = {
    "ogohlantiruvchi": "⚠️ 1. Ogohlantiruvchi belgilar",
    "imtiyozli": "🛑 2. Imtiyozli belgilar",
    "taqiqlovchi": "🚫 3. Taqiqlovchi belgilar",
    "buyuruvchi": "⬆️ 4. Buyuruvchi belgilar",
    "axborot": "ℹ️ 5. Axborot-ko'rsatkich belgilari",
    "servis": "🛠 6. Servis belgilari",
}

# ─── ASOSIY MENYU ──────────────────────────────────────────────────
def get_signs_hub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ 1. Ogohlantiruvchi", callback_data="signs_cat_ogohlantiruvchi"),
            InlineKeyboardButton(text="🛑 2. Imtiyozli", callback_data="signs_cat_imtiyozli")
        ],
        [
            InlineKeyboardButton(text="🚫 3. Taqiqlovchi", callback_data="signs_cat_taqiqlovchi"),
            InlineKeyboardButton(text="⬆️ 4. Buyuruvchi", callback_data="signs_cat_buyuruvchi")
        ],
        [
            InlineKeyboardButton(text="ℹ️ 5. Axborot", callback_data="signs_cat_axborot"),
            InlineKeyboardButton(text="🛠 6. Servis", callback_data="signs_cat_servis")
        ],
        [
            InlineKeyboardButton(text="🔍 Belgini qidirish", callback_data="signs_search"),
            InlineKeyboardButton(text="📝 Belgilar bo'yicha test", callback_data="signs_test")
        ],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_main_menu")]
    ])

@signs_router.message(F.text.in_([
    "🚦 Yo'l belgilari", "⚠️ Yo'l Belgilari", "🚦 Yo'l Belgilari", "⚠️ Yo'l belgilari",
    "🚦 Йўл белгилари", "🚦 Дорожные знаки", "🚦 Belgilar"
]))
async def signs_menu(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    text = (
        "🚦 <b>O'ZBEKISTON RESPUBLIKASI YO'L BELGILARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Yo'l harakati qoidalarida belgilangan rasmiy 6 ta asosiy guruhdagi barcha 130 ta belgi:\n\n"
        "⚠️ <b>1. Ogohlantiruvchi:</b> Xavfli yo'l qismlari haqida ogohlantiradi\n"
        "🛑 <b>2. Imtiyozli:</b> Chorrahalarda o'tish navbatini belgilaydi\n"
        "🚫 <b>3. Taqiqlovchi:</b> Harakatlanishga muayyan cheklovlar kiritadi\n"
        "⬆️ <b>4. Buyuruvchi:</b> Belgilangan yo'nalishda harakatlanishni buyuradi\n"
        "ℹ️ <b>5. Axborot-ko'rsatkich:</b> Hududlar va maxsus harakat tartiblari\n"
        "🛠 <b>6. Servis:</b> Yo'ldagi xizmat ko'rsatish maskanlari\n\n"
        "👇 <i>O'rganmoqchi bo'lgan guruhni tanlang:</i>"
    )
    await message.answer(text, reply_markup=get_signs_hub_keyboard(), parse_mode="HTML")


# ─── KATEGORIYA BELGILARI (SAHIFALANGAN) ───────────────────────────
@signs_router.callback_query(F.data.startswith("signs_cat_") | F.data.startswith("signs_page_"))
async def show_signs_category(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    # signs_cat_taqiqlovchi or signs_page_taqiqlovchi_2
    if parts[1] == "cat":
        category = parts[2]
        page = 1
    else:
        category = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 1

    # Alias imtiyoz -> imtiyozli
    db_category = "imtiyozli" if category in ["imtiyoz", "imtiyozli"] else category

    async with async_session() as session:
        result = await session.execute(
            select(Sign).where(Sign.category == db_category).order_by(Sign.id)
        )
        signs = result.scalars().all()

    cat_title = CAT_LABELS.get(db_category, db_category.capitalize())

    if not signs:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data="signs_back")]
        ])
        msg_text = f"<b>{cat_title}</b>\n\nHozircha bu guruhda belgilar kiritilmagan."
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(msg_text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    total_signs = len(signs)
    total_pages = (total_signs + SIGNS_PER_PAGE - 1) // SIGNS_PER_PAGE
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * SIGNS_PER_PAGE
    end_idx = start_idx + SIGNS_PER_PAGE
    page_signs = signs[start_idx:end_idx]

    buttons = []
    for s in page_signs:
        buttons.append([InlineKeyboardButton(
            text=f"🚸 {s.name[:55]}",
            callback_data=f"sign_{s.id}_{page}"
        )])

    # Sahifalash (Navigatsiya)
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"signs_page_{category}_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="signs_nop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"signs_page_{category}_{page + 1}"))

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔙 Bo'limlar katalogi", callback_data="signs_back"),
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = (
        f"<b>{cat_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Ushbu guruhda jami: <b>{total_signs} ta belgi</b> (Sahifa {page}/{total_pages})\n\n"
        f"👇 <i>Tafsilotini ko'rish uchun belgini tanlang:</i>"
    )

    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@signs_router.callback_query(F.data == "signs_nop")
async def signs_nop(callback: types.CallbackQuery):
    await callback.answer()


# ─── BELGI TAFSILOTI ───────────────────────────────────────────────
@signs_router.callback_query(F.data.startswith("sign_"))
async def show_sign_detail(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    sign_id = int(parts[1])
    back_page = int(parts[2]) if len(parts) > 2 else 1

    async with async_session() as session:
        result = await session.execute(select(Sign).where(Sign.id == sign_id))
        sign = result.scalars().first()

    if not sign:
        await callback.answer("❌ Belgi topilmadi.", show_alert=True)
        return

    cat_title = CAT_LABELS.get(sign.category, sign.category.capitalize())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data=f"signs_page_{sign.category}_{back_page}")],
        [
            InlineKeyboardButton(text="📝 Belgilar testi", callback_data="signs_test"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="back_to_main_menu")
        ]
    ])

    text = (
        f"🚦 <b>{sign.name.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📂 <b>Guruh:</b> {cat_title}\n\n"
        f"📖 <b>Qoidasi va ta'rifi:</b>\n{sign.description or 'Yo\'l harakati xavfsizligini ta\'minlash uchun o\'rnatiladi.'}\n\n"
        f"💡 <b>Misol / Amal qilish tartibi:</b>\n{sign.example or 'Yo\'l harakati qoidalariga qat\'iy rioya qiling.'}"
    )

    photo_to_send = None
    if sign.image_url:
        if not str(sign.image_url).startswith("http"):
            raw_url = str(sign.image_url).replace('\\', '/')
            base_fname = os.path.basename(raw_url)
            cand_paths = [
                os.path.join(BASE_DIR, "images", "signs", base_fname),
                os.path.join(BASE_DIR, raw_url),
                os.path.join(BASE_DIR, raw_url.replace("webapp/", ""))
            ]
            for cand in cand_paths:
                if os.path.exists(cand) and os.path.getsize(cand) > 100:
                    photo_to_send = FSInputFile(cand)
                    break
        else:
            photo_to_send = sign.image_url

    await callback.answer()

    if photo_to_send:
        try:
            if callback.message.photo:
                await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo_to_send,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        except Exception as e:
            print(f"Error sending sign photo: {e}")

    # Fallback to text
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ─── QIDIRISH (FSM) ────────────────────────────────────────────────
@signs_router.callback_query(F.data == "signs_search")
async def signs_search_prompt(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="signs_back")]
    ])
    text_content = (
        "🔍 <b>YO'L BELGISINI QIDIRISH</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Qidirmoqchi bo'lgan belgining <b>raqami</b> yoki <b>nomini</b> yozib yuboring:\n\n"
        "Masalan: <code>3.24</code>, <code>to'xtash</code>, <code>asosiy yo'l</code> yoki <code>piyodalar</code>"
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text_content, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(SignStates.searching)
    await callback.answer()


@signs_router.message(SignStates.searching)
async def signs_search_result(message: types.Message, state: FSMContext):
    query = message.text.strip().lower()
    await state.clear()

    async with async_session() as session:
        result = await session.execute(select(Sign).order_by(Sign.id))
        all_signs = result.scalars().all()

    found = [
        s for s in all_signs
        if query in s.name.lower() or (s.description and query in s.description.lower())
    ]

    if not found:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="signs_search")],
            [InlineKeyboardButton(text="🔙 Belgilar katalogiga", callback_data="signs_back")]
        ])
        await message.answer(
            f"❌ «<b>{message.text}</b>» bo'yicha hech qanday yo'l belgisi topilmadi.\n\n"
            f"Belgining raqami (masalan <code>1.1</code>) yoki nomi bilan qayta urinib ko'ring.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    buttons = []
    for s in found[:15]:
        buttons.append([InlineKeyboardButton(
            text=f"🚸 {s.name[:50]}",
            callback_data=f"sign_{s.id}_1"
        )])
    buttons.append([
        InlineKeyboardButton(text="🔍 Boshqa qidirish", callback_data="signs_search"),
        InlineKeyboardButton(text="🔙 Katalogga qaytish", callback_data="signs_back")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🔍 «<b>{message.text}</b>» bo'yicha qidiruv natijalari:\n"
        f"Topildi: <b>{len(found)} ta</b> belgi\n\n"
        f"👇 <i>Kerakli belgini tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ─── ORQAGA ──────────────────────────────────────────────────────
@signs_router.callback_query(F.data == "signs_back")
async def signs_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🚦 <b>O'ZBEKISTON RESPUBLIKASI YO'L BELGILARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Yo'l harakati qoidalarida belgilangan rasmiy 6 ta asosiy guruhdagi barcha 130 ta belgi.\n\n"
        "👇 <i>O'rganmoqchi bo'lgan guruhni tanlang:</i>"
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_signs_hub_keyboard(), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=get_signs_hub_keyboard(), parse_mode="HTML")
    await callback.answer()


# ─── BELGILAR BO'YICHA TEST ─────────────────────────────────────
@signs_router.callback_query(F.data == "signs_test")
async def signs_test(callback: types.CallbackQuery, state: FSMContext):
    from database import Question
    from sqlalchemy.sql.expression import func
    from handlers.test import TestStates, send_question

    async with async_session() as session:
        result = await session.execute(
            select(Question).where(
                (Question.category.like("%belgi%")) | (Question.text.like("%belgi%"))
            ).order_by(func.random()).limit(10)
        )
        questions = result.scalars().all()
        if not questions or len(questions) < 10:
            result_all = await session.execute(
                select(Question).where(Question.image_url != None).order_by(func.random()).limit(10)
            )
            questions = result_all.scalars().all()

    if not questions:
        await callback.answer("Hozircha belgilar bo'yicha savollar topilmadi.", show_alert=True)
        return

    q_ids = [q.id for q in questions]
    await state.set_state(TestStates.taking_test)
    await state.update_data(
        questions=q_ids, current_idx=0, correct_answers=0, wrong_count=0,
        selected_category="Yo'l belgilari", is_gai_mode=False, is_marathon_mode=False, is_video_mode=False
    )
    try:
        await callback.message.delete()
    except Exception:
        pass

    await send_question(callback, state)
