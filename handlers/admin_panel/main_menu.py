from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.permissions import is_any_admin, is_superadmin, check_permission

main_menu_router = Router()

async def get_pro_admin_keyboard(user_id: int):
    keyboard = []
    
    # 1. Statistika va Broadcast
    row1 = []
    if await check_permission(user_id, "can_view_stats"):
        row1.append(InlineKeyboardButton(text="📊 Statistika & Excel", callback_data="admin_stats"))
    if await check_permission(user_id, "can_broadcast"):
        row1.append(InlineKeyboardButton(text="📢 Xabar Tarqatish", callback_data="admin_broadcast"))
    if row1: keyboard.append(row1)
    
    # 2. Savollar va Belgilar
    row2 = []
    if await check_permission(user_id, "can_manage_content"):
        row2.append(InlineKeyboardButton(text="📝 Savollar (805 ta)", callback_data="admin_tests"))
        row2.append(InlineKeyboardButton(text="🚦 Yo'l Belgilari", callback_data="admin_signs"))
    if row2: keyboard.append(row2)
    
    # 3. YHQ Qoidalari va Videolar
    row3 = []
    if await check_permission(user_id, "can_manage_content"):
        row3.append(InlineKeyboardButton(text="📚 YHQ Qoidalari", callback_data="admin_rules"))
        row3.append(InlineKeyboardButton(text="🎥 Video Darslar", callback_data="admin_videos"))
    if row3: keyboard.append(row3)
    
    # 4. VIP To'lovlar, Guruhlar va Avtomaktab
    row4 = []
    if await check_permission(user_id, "can_manage_premium"):
        row4.append(InlineKeyboardButton(text="💳 VIP & Promokodlar", callback_data="admin_premium"))
    if await check_permission(user_id, "can_manage_groups"):
        row4.append(InlineKeyboardButton(text="👥 Guruhlar & Kanallar", callback_data="admin_groups"))
    if row4: keyboard.append(row4)

    # 5. Avtomaktab O'quvchilari va Tashkilot/O'qish
    if await check_permission(user_id, "can_manage_content"):
        keyboard.append([
            InlineKeyboardButton(text="🎓 O'quvchilar Bazasi", callback_data="admin_school"),
            InlineKeyboardButton(text="🏢 Tashkilot & O'qish", callback_data="admin_org_hub")
        ])
    
    # 6. Tizim va Adminlar boshqaruvi (faqat superadmin uchun)
    if is_superadmin(user_id):
        keyboard.append([
            InlineKeyboardButton(text="👮 Adminlar Boshqaruvi", callback_data="adm_mgmt"),
            InlineKeyboardButton(text="⚙️ Tizim Sozlamalari", callback_data="admin_system")
        ])
    # 7. Menyuga qaytish
    keyboard.append([
        InlineKeyboardButton(text="❌ Admin paneldan chiqish", callback_data="back_to_main_menu")
    ])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@main_menu_router.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not await is_any_admin(message.from_user.id):
        await message.answer("❌ Kechirasiz, sizda administratorlik huquqi mavjud emas.")
        return
        
    kb = await get_pro_admin_keyboard(message.from_user.id)
    status_role = "👑 Bosh Administrator" if is_superadmin(message.from_user.id) else "👮 Moderator"
    text = (
        "👑 <b>VATANPARVAR AVTOTEST — BOSHQARUV MARKAZI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Administrator:</b> {message.from_user.full_name}\n"
        f"🎖 <b>Mansab:</b> <i>{status_role}</i>\n"
        "🟢 <b>Tizim holati:</b> Faol (805 ta rasmiy test)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Quyidagi bo'limlardan birini tanlang:</i>"
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@main_menu_router.callback_query(F.data == "admin_back_main")
async def admin_back_main(callback: types.CallbackQuery):
    if not await is_any_admin(callback.from_user.id):
        return
        
    kb = await get_pro_admin_keyboard(callback.from_user.id)
    status_role = "👑 Bosh Administrator" if is_superadmin(callback.from_user.id) else "👮 Moderator"
    text = (
        "👑 <b>VATANPARVAR AVTOTEST — BOSHQARUV MARKAZI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Administrator:</b> {callback.from_user.full_name}\n"
        f"🎖 <b>Mansab:</b> <i>{status_role}</i>\n"
        "🟢 <b>Tizim holati:</b> Faol (805 ta rasmiy test)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Quyidagi bo'limlardan birini tanlang:</i>"
    )
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
