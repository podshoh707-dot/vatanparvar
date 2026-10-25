import os
import json
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from database import async_session, Setting
from sqlalchemy import select
from utils.permissions import check_permission, is_superadmin
from config import BASE_DIR, ADMIN_IDS

organization_router = Router()

DEFAULT_ORG_DATA = {
    "title": "AVTOVATANPARVAR INNOVATSION AVTOMAKTABI",
    "about": "O'zbekistonda yoshlarni va barcha qiziquvchilarni haydovchilik sirlariga o'rgatish, yo'l harakati xavfsizligini oshirish maqsadida tashkil etilgan zamonaviy o'quv maskani.\n\nSifatli ta'lim, malakali ustozlar va eng so'nggi texnologiyalar yordamida haydovchilik sirlari o'rgatiladi.",
    "categories": (
        "🏍 A toifa — 2 200 000 so'm\n"
        "🚗 B toifa — 6 100 000 so'm\n"
        "🚙 BC toifa — 8 100 000 so'm\n"
        "🚚 C toifa — 3 200 000 so'm\n"
        "🚛 E toifa — 3 200 000 so'm\n"
        "🚌 D toifa — 5 200 000 so'm"
    ),
    "documents": (
        "1️⃣ Pasport yoki ID karta nusxasi\n"
        "2️⃣ 083/h shakldagi tibbiy ma'lumotnoma\n"
        "3️⃣ 3x4 o'lchamdagi 4 dona rasm"
    ),
    "phone": "+998 97 069 70 77",
    "address": "Toshkent shahri",
    "admin_username": "@Avto_admin",
    "photo_id": "org_banner.png"
}


class OrgEditStates(StatesGroup):
    editing_about = State()
    editing_prices = State()
    editing_docs = State()
    editing_contacts = State()
    editing_photo = State()
    editing_full = State()


async def get_org_data() -> dict:
    """DB dan yoki JSON fayldan tashkilot ma'lumotlarini yuklash"""
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        if setting and setting.value:
            try:
                data = json.loads(setting.value)
                return {**DEFAULT_ORG_DATA, **data}
            except Exception:
                pass

    # Database JSON faylidan tekshirish
    json_path = os.path.join(BASE_DIR, "database", "org_info.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                return {**DEFAULT_ORG_DATA, **d}
        except Exception:
            pass

    return DEFAULT_ORG_DATA.copy()


async def save_org_data(data: dict):
    """DB ga va database/org_info.json ga saqlash"""
    val_json = json.dumps(data, ensure_ascii=False, indent=2)

    # 1. DB ga yozish
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="org_info", value=val_json)
            session.add(setting)
        else:
            setting.value = val_json
        await session.commit()

    # 2. database/org_info.json ga yozish
    db_json = os.path.join(BASE_DIR, "database", "org_info.json")
    try:
        with open(db_json, "w", encoding="utf-8") as f:
            f.write(val_json)
    except Exception as e:
        print(f"Error saving to database/org_info.json: {e}")


def format_org_preview_text(data: dict) -> str:
    photo_status = "🖼 Mavjud" if data.get("photo_id") else "❌ Yo'q"
    return (
        "🏢 <b>TASHKILOT VA O'QISH MA'LUMOTLARI BOSHQARUVI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏛 <b>Nomi:</b> {data.get('title', '')}\n\n"
        f"📝 <b>Tashkilot haqida:</b>\n<i>{data.get('about', '')}</i>\n\n"
        f"🎓 <b>O'qish toifalari va narxlar:</b>\n{data.get('categories', '')}\n\n"
        f"📑 <b>Kerakli hujjatlar:</b>\n{data.get('documents', '')}\n\n"
        f"📞 <b>Aloqa telefoni:</b> {data.get('phone', '')}\n"
        f"📍 <b>Manzil:</b> {data.get('address', '')}\n"
        f"💬 <b>Admin:</b> {data.get('admin_username', '')}\n"
        f"🖼 <b>Banner rasmi:</b> {photo_status}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Quyidagi tugmalar orqali istalgan ma'lumotni tahrirlashingiz mumkin:</i>"
    )


def get_org_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Tashkilot tavsifi", callback_data="org_edit_about"),
            InlineKeyboardButton(text="🎓 Toifalar & Narxlar", callback_data="org_edit_prices")
        ],
        [
            InlineKeyboardButton(text="📑 Kerakli hujjatlar", callback_data="org_edit_docs"),
            InlineKeyboardButton(text="📞 Telefon & Manzil", callback_data="org_edit_contacts")
        ],
        [
            InlineKeyboardButton(text="🖼 Banner rasmini almashtirish", callback_data="org_edit_photo"),
            InlineKeyboardButton(text="✍️ To'liq matn (Hammasi)", callback_data="org_edit_full")
        ],
        [
            InlineKeyboardButton(text="👁 Botda qanday ko'rinishini tekshirish", callback_data="org_preview_user"),
            InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="admin_back_main")
        ]
    ])


# ══════════════════════════════════════════════════════════════════════════════
# ASOSIY MENU
# ══════════════════════════════════════════════════════════════════════════════
@organization_router.message(F.text.in_(["🏢 Tashkilot & O'qish", "🏢 Tashkilot", "🏢 Tashkilot va O'qish"]))
async def msg_org_hub(message: types.Message, state: FSMContext = None):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    if state:
        await state.clear()
    data = await get_org_data()
    text = format_org_preview_text(data)
    await message.answer(text, reply_markup=get_org_admin_kb(), parse_mode="HTML")


@organization_router.callback_query(F.data == "admin_org_hub")
async def admin_org_hub(callback: types.CallbackQuery, state: FSMContext = None):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return

    if state:
        await state.clear()

    data = await get_org_data()
    text = format_org_preview_text(data)
    await callback.message.edit_text(text, reply_markup=get_org_admin_kb(), parse_mode="HTML")
    await callback.answer()


# ── 1. Tashkilot tavsifi ──────────────────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_about")
async def org_edit_about_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_about)
    await callback.message.edit_text(
        "📝 <b>Tashkilot haqida yangi tavsif matnini yuboring:</b>\n\n"
        "(HTML teglari: <b>qalin</b>, <i>kursiv</i> ishlatishingiz mumkin)\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_about)
async def org_save_about(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Tahrirlash bekor qilindi. /admin")
        return

    val = message.html_text or message.text or ""
    data = await get_org_data()
    data["about"] = val
    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>Tashkilot tavsifi muvaffaqiyatli saqlandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 2. O'qish toifalari & Narxlar ─────────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_prices")
async def org_edit_prices_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_prices)
    await callback.message.edit_text(
        "🎓 <b>O'qish toifalari va narxlarini yangi ro'yxatini yuboring:</b>\n\n"
        "<i>Namuna:</i>\n"
        "🏍 A toifa — 2 200 000 so'm\n"
        "🚗 B toifa — 6 100 000 so'm\n"
        "🚙 BC toifa — 8 100 000 so'm\n"
        "🚚 C toifa — 3 200 000 so'm\n"
        "🚛 E toifa — 3 200 000 so'm\n"
        "🚌 D toifa — 5 200 000 so'm\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_prices)
async def org_save_prices(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Tahrirlash bekor qilindi. /admin")
        return

    val = message.html_text or message.text or ""
    data = await get_org_data()
    data["categories"] = val
    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>O'qish toifalari va narxlari muvaffaqiyatli saqlandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 3. Kerakli hujjatlar ──────────────────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_docs")
async def org_edit_docs_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_docs)
    await callback.message.edit_text(
        "📑 <b>O'qishga kirish uchun kerakli hujjatlar ro'yxatini yuboring:</b>\n\n"
        "<i>Namuna:</i>\n"
        "1️⃣ Pasport yoki ID karta nusxasi\n"
        "2️⃣ 083/h shakldagi tibbiy ma'lumotnoma\n"
        "3️⃣ 3x4 o'lchamdagi 4 dona rasm\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_docs)
async def org_save_docs(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Tahrirlash bekor qilindi. /admin")
        return

    val = message.html_text or message.text or ""
    data = await get_org_data()
    data["documents"] = val
    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>Kerakli hujjatlar ro'yxati muvaffaqiyatli saqlandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 4. Telefon va Manzil ─────────────────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_contacts")
async def org_edit_contacts_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_contacts)
    await callback.message.edit_text(
        "📞 <b>Aloqa telefoni, manzil va admin username'ini quyidagi formatda yuboring:</b>\n\n"
        "<i>Format:</i>\n"
        "Telefon: +998 97 069 70 77\n"
        "Manzil: Toshkent shahri, Chilonzor\n"
        "Admin: @Avto_admin\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_contacts)
async def org_save_contacts(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Tahrirlash bekor qilindi. /admin")
        return

    text = message.text or ""
    lines = text.strip().split("\n")
    data = await get_org_data()
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            k_lower = k.strip().lower()
            v_clean = v.strip()
            if "telefon" in k_lower or "aloqa" in k_lower:
                data["phone"] = v_clean
            elif "manzil" in k_lower:
                data["address"] = v_clean
            elif "admin" in k_lower:
                data["admin_username"] = v_clean

    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>Aloqa ma'lumotlari muvaffaqiyatli saqlandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 5. Banner Rasmi ──────────────────────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_photo")
async def org_edit_photo_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_photo)
    await callback.message.edit_text(
        "🖼 <b>Tashkilotning yangi banner rasmini (Photo) yuboring:</b>\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_photo, F.photo)
async def org_save_photo(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return

    photo_id = message.photo[-1].file_id
    data = await get_org_data()
    data["photo_id"] = photo_id
    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>Yangi banner rasmi muvaffaqiyatli saqlandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 6. To'liq matn (Rasm + Matn birga) ────────────────────────────────────────
@organization_router.callback_query(F.data == "org_edit_full")
async def org_edit_full_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return
    await state.set_state(OrgEditStates.editing_full)
    await callback.message.edit_text(
        "✍️ <b>Barcha ma'lumotlarni bitta xabarda yuboring:</b>\n\n"
        "Rasmni biriktirib, ostiga to'liq tavsif, narxlar va aloqa ma'lumotlarini yozib bitta post qilib yuborishingiz mumkin.\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_org_hub")]]),
        parse_mode="HTML"
    )
    await callback.answer()


@organization_router.message(OrgEditStates.editing_full)
async def org_save_full(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Tahrirlash bekor qilindi. /admin")
        return

    text = message.html_text or message.caption or message.text or ""
    photo_id = message.photo[-1].file_id if message.photo else None

    data = await get_org_data()
    data["about"] = text
    if photo_id:
        data["photo_id"] = photo_id

    await save_org_data(data)
    await state.clear()
    await message.answer("✅ <b>Barcha ma'lumotlar saqlandi va yangilandi!</b>\n\n/admin - boshqaruv markaziga qaytish", parse_mode="HTML")


# ── 7. Foydalanuvchiga qanday ko'rinishini tekshirish ─────────────────────────
@organization_router.callback_query(F.data == "org_preview_user")
async def org_preview_user(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        return

    data = await get_org_data()
    text = (
        f"🏛 <b>{data.get('title', 'AVTOVATANPARVAR INNOVATSION AVTOMAKTABI')}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{data.get('about', '')}\n\n"
        "📋 <b>Bizda quyidagi toifalar bo'yicha o'qitiladi va narxlar:</b>\n"
        f"{data.get('categories', '')}\n\n"
        "📑 <b>O'qish uchun kerakli hujjatlar:</b>\n"
        f"{data.get('documents', '')}\n\n"
        f"📍 <b>Manzil:</b> {data.get('address', 'Toshkent shahri')}\n"
        f"📞 <b>Aloqa telefoni:</b> {data.get('phone', '+998 97 069 70 77')}\n\n"
        "<i>Biz bilan professionallar safiga qo'shiling!</i>"
    )
    admin_u = data.get('admin_username', '@Avto_admin')
    if not admin_u.startswith('@'): admin_u = '@' + admin_u
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Adminga murojaat", url=f"https://t.me/{admin_u[1:]}")],
        [InlineKeyboardButton(text="🔙 Admin panelga", callback_data="admin_org_hub")]
    ])

    photo_obj = None
    photo_id = data.get("photo_id")
    if photo_id:
        if photo_id.endswith(".png") or photo_id.endswith(".jpg"):
            local_p = os.path.join(BASE_DIR, photo_id)
            if os.path.exists(local_p):
                photo_obj = FSInputFile(local_p)
        else:
            photo_obj = photo_id

    try:
        if photo_obj:
            await callback.message.answer_photo(photo=photo_obj, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

    await callback.answer()
