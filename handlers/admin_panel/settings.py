from aiogram import Router, types, F, Bot
from utils.permissions import check_permission, is_superadmin
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, User, Setting
from sqlalchemy import select
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from config import ADMIN_IDS

settings_router = Router()

class PremiumStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_user_id = State()
    waiting_for_tariff_price = State()
    waiting_for_tariff_text = State()



@settings_router.message(F.text.in_(["💳 VIP & Promokodlar", "💳 VIP", "💳 Promokodlar", "💳 VIP Sozlamalari"]))
async def msg_premium_menu(message: types.Message):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        setting = result.scalars().first()
        is_on = setting.value == "1" if setting else False
        status_text = "🟢 Yoqilgan" if is_on else "🔴 O'chirilgan"
        
        result_card = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        card_setting = result_card.scalars().first()
        card_num = card_setting.value if card_setting else "O'rnatilmagan"
        
        result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        price_setting = result_price.scalars().first()
        tariff_price = price_setting.value if price_setting else "O'rnatilmagan"
        
        result_text = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        text_setting = result_text.scalars().first()
        tariff_text = text_setting.value if text_setting else "O'rnatilmagan"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Premium reja: {status_text}", callback_data="admin_toggle_premium")],
        [
            InlineKeyboardButton(text="🎟 +5 ta Promokod Yaratish", callback_data="admin_gen_promos"),
            InlineKeyboardButton(text="📋 Barcha Promokodlar", callback_data="admin_list_promos")
        ],
        [
            InlineKeyboardButton(text="💳 Karta raqami", callback_data="admin_set_card"),
            InlineKeyboardButton(text="💵 Tarif narxi", callback_data="admin_set_price")
        ],
        [InlineKeyboardButton(text="🧾 Kutilayotgan To'lov Cheklari", callback_data="admin_pending_payments")],
        [InlineKeyboardButton(text="🎁 Foydalanuvchiga VIP berish", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])
    
    text = (
        f"💰 <b>PREMIUM VA TO'LOVLAR BOSHQARUVI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card_num}</code>\n"
        f"💵 <b>Tarif narxi:</b> <code>{tariff_price}</code>\n"
        f"📝 <b>Tarif tavsifi:</b>\n<i>{tariff_text}</i>\n\n"
        f"Kerakli amalni tanlang:"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@settings_router.callback_query(F.data == "admin_premium")
async def admin_premium(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        setting = result.scalars().first()
        is_on = setting.value == "1" if setting else False
        status_text = "🟢 Yoqilgan" if is_on else "🔴 O'chirilgan"
        
        result_card = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        card_setting = result_card.scalars().first()
        card_num = card_setting.value if card_setting else "O'rnatilmagan"
        
        result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        price_setting = result_price.scalars().first()
        tariff_price = price_setting.value if price_setting else "O'rnatilmagan"
        
        result_text = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        text_setting = result_text.scalars().first()
        tariff_text = text_setting.value if text_setting else "O'rnatilmagan"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Premium reja: {status_text}", callback_data="admin_toggle_premium")],
        [
            InlineKeyboardButton(text="🎟 +5 ta Promokod Yaratish", callback_data="admin_gen_promos"),
            InlineKeyboardButton(text="📋 Barcha Promokodlar", callback_data="admin_list_promos")
        ],
        [
            InlineKeyboardButton(text="💳 Karta raqami", callback_data="admin_set_card"),
            InlineKeyboardButton(text="💵 Tarif narxi", callback_data="admin_set_price")
        ],
        [InlineKeyboardButton(text="🧾 Kutilayotgan To'lov Cheklari", callback_data="admin_pending_payments")],
        [InlineKeyboardButton(text="🎁 Foydalanuvchiga VIP berish", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]
    ])
    
    await callback.message.edit_text(
        f"💰 <b>PREMIUM VA TO'LOVLAR BOSHQARUVI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card_num}</code>\n"
        f"💵 <b>Tarif narxi:</b> <code>{tariff_price}</code>\n"
        f"📝 <b>Tarif tavsifi:</b>\n<i>{tariff_text}</i>\n\n"
        f"👇 <i>Kerakli amalni tanlang:</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@settings_router.callback_query(F.data == "admin_toggle_premium")
async def toggle_premium(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
        setting = result.scalars().first()
        
        if not setting:
            setting = Setting(key="premium_mode", value="1")
            session.add(setting)
        else:
            setting.value = "0" if setting.value == "1" else "1"
        
        await session.commit()
    
    await admin_premium(callback)

@settings_router.callback_query(F.data == "admin_set_card")
async def set_card_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    await callback.message.edit_text("Yangi karta raqamini yozib yuboring (Masalan: 8600 1234 5678 9012):")
    await state.set_state(PremiumStates.waiting_for_card)

@settings_router.message(PremiumStates.waiting_for_card)
async def set_card_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
        
    new_card = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "admin_card"))
        setting = result.scalars().first()
        
        if not setting:
            setting = Setting(key="admin_card", value=new_card)
            session.add(setting)
        else:
            setting.value = new_card
            
        await session.commit()
        
    await state.clear()
    await message.answer(f"✅ Karta raqami muvaffaqiyatli saqlandi: {new_card}\n/admin orqali panelga qaytishingiz mumkin.")

@settings_router.callback_query(F.data == "admin_give_premium")
async def give_premium_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
    ])
    await callback.message.edit_text(
        "🎁 <b>Foydalanuvchiga VIP berish:</b>\n\n"
        "VIP Premium berish kerak bo'lgan foydalanuvchining Telegram ID sini yozing:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(PremiumStates.waiting_for_user_id)

@settings_router.message(PremiumStates.waiting_for_user_id)
async def give_premium_save(message: types.Message, state: FSMContext, bot: Bot):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    text = (message.text or "").strip()
    if text.startswith("/") or text in ["🔙 Orqaga", "Bekor qilish"]:
        await state.clear()
        await message.answer("VIP berish bekor qilindi.")
        return
    try:
        target_id = int(text)
    except ValueError:
        await message.answer("❌ Faqat raqam (Telegram ID) kiriting:")
        return
        
    from database import Payment
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == target_id))
        user = result.scalars().first()
        if not user:
            await message.answer("❌ Bu ID ga ega foydalanuvchi bot bazasida topilmadi. Foydalanuvchi avval botda /start bosgan bo'lishi kerak.")
            return
            
        now = datetime.utcnow()
        if user.is_premium and user.premium_expires_at and user.premium_expires_at > now:
            user.premium_expires_at += timedelta(days=30)
        else:
            user.is_premium = True
            user.premium_expires_at = now + timedelta(days=30)
            
        payment = Payment(
            user_telegram_id=target_id,
            user_full_name=user.full_name,
            amount="Admin sovg'asi (+30 kun)",
            status="approved",
            days_granted=30,
            approved_by=message.from_user.id,
            resolved_at=now
        )
        session.add(payment)
        await session.commit()
        exp_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M')

    try:
        kb_user = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚗 Testlarni boshlash", callback_data="testcnt_gai")],
            [InlineKeyboardButton(text="👑 Bosh menyu", callback_data="back_to_main_menu")]
        ])
        await bot.send_message(
            target_id,
            f"🎉 <b>TABRIKLAYMIZ! SIZGA VIP PREMIUM SOVG'A QILINDI!</b>\n"
            f"───────────────────────────\n\n"
            f"Admin tomonidan sizga <b>30 kunlik VIP Premium</b> taqdim etildi.\n"
            f"⏳ Amal qilish muddati: <b>{exp_str} gacha</b>.\n\n"
            f"👑 <i>Endi barcha VIP imkoniyatlardan cheksiz foydalanishingiz mumkin!</i>",
            reply_markup=kb_user,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()
    await message.answer(
        f"✅ <code>{target_id}</code> ID egasiga <b>30 kunlik VIP Premium</b> muvaffaqiyatli berildi!\n"
        f"⏳ Amal qilish muddati: <b>{exp_str}</b>\n\n"
        f"/admin orqali panelga qaytishingiz mumkin.",
        parse_mode="HTML"
    )

@settings_router.callback_query(F.data == "admin_set_price")
async def set_price_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("1 oylik Premium tarif narxini yozing (Masalan: 15 000 so'm):")
    await state.set_state(PremiumStates.waiting_for_tariff_price)

@settings_router.message(PremiumStates.waiting_for_tariff_price)
async def set_price_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    new_price = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="tariff_price", value=new_price)
            session.add(setting)
        else:
            setting.value = new_price
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Tarif narxi saqlandi: {new_price}\n/admin orqali panelga qaytishingiz mumkin.")

@settings_router.callback_query(F.data == "admin_set_text")
async def set_text_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("Tarif haqida to'liq matnni yozing (afzalliklari va shartlari):")
    await state.set_state(PremiumStates.waiting_for_tariff_text)

@settings_router.message(PremiumStates.waiting_for_tariff_text)
async def set_text_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_premium"):
        await message.answer("Sizda bu bo'limga ruxsat yo'q!")
        return
    new_text = message.text
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="tariff_text", value=new_text)
            session.add(setting)
        else:
            setting.value = new_text
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Tarif matni saqlandi.\n/admin orqali panelga qaytishingiz mumkin.")

class OrgStates(StatesGroup):
    waiting_for_org_text = State()

@settings_router.callback_query(F.data == "admin_org_edit")
async def org_edit_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not await check_permission(callback.from_user.id, "can_manage_content"):
        await callback.answer("Sizda bu bo'limga ruxsat yo'q!", show_alert=True)
        return
        
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        current_text = "Hali kiritilmagan."
        if setting:
            import json
            try:
                data = json.loads(setting.value)
                current_text = data.get("text", "")
            except:
                current_text = setting.value
        
    await callback.message.edit_text(
        f"🏢 Tashkilot haqida ma'lumot:\n\n{current_text[:800]}\n\nYangi ma'lumotni yuboring (Rasm va matnni birga yuborishingiz ham mumkin):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back_main")]])
    )
    await state.set_state(OrgStates.waiting_for_org_text)

@settings_router.message(OrgStates.waiting_for_org_text)
async def org_edit_save(message: types.Message, state: FSMContext):
    if not await check_permission(message.from_user.id, "can_manage_content"):
        return
        
    text = message.html_text or message.text or ""
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
        
    import json
    val = json.dumps({"text": text, "photo_id": photo_id}, ensure_ascii=False)
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "org_info"))
        setting = result.scalars().first()
        if not setting:
            setting = Setting(key="org_info", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
        
    await state.clear()
    await message.answer("✅ Tashkilot ma'lumotlari saqlandi.\n/admin orqali panelga qaytishingiz mumkin.")


# ──────────────── PROMO KOD GENERATORI ────────────────
@settings_router.callback_query(F.data == "admin_gen_promos")
async def generate_promocodes_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    import secrets
    from database import PromoCode
    
    generated = []
    async with async_session() as session:
        for _ in range(5):
            code = f"VIP-{secrets.token_hex(3).upper()}"
            promo = PromoCode(code=code, days_granted=30, is_active=True)
            session.add(promo)
            generated.append(code)
        await session.commit()
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yana +5 ta yaratish", callback_data="admin_gen_promos")],
        [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
    ])
    
    list_str = "\n".join([f"<code>{c}</code> (30 kunlik VIP)" for c in generated])
    msg_text = (
        "🎟 <b>5 TA YANGI VIP PROMOKOD YARATILDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{list_str}\n\n"
        "<i>(Promokodni nusxalash uchun ustiga bosing va o'quvchilarga yoki kanalga ulashing)</i>"
    )
    await callback.message.edit_text(msg_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer("✅ 5 ta yangi promokod yaratildi!")


# ──────────────── BARCHA PROMOKODLAR RO'YXATI ────────────────
@settings_router.callback_query(F.data == "admin_list_promos")
async def list_promocodes_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    from database import PromoCode
    async with async_session() as session:
        result = await session.execute(
            select(PromoCode).where(PromoCode.is_active == True).order_by(PromoCode.id.desc()).limit(20)
        )
        promos = result.scalars().all()
        
    if not promos:
        text = "📋 <b>Ayni damda faol promokodlar yo'q.</b>\n\nQuyidagi tugma orqali yangi promokodlar yaratishingiz mumkin:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎟 +5 ta Promokod Yaratish", callback_data="admin_gen_promos")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
    else:
        promo_lines = []
        for i, p in enumerate(promos, 1):
            promo_lines.append(f"{i}. <code>{p.code}</code> — {p.days_granted} kunlik VIP")
            
        text = (
            f"📋 <b>FAOL PROMOKODLAR (Jami: {len(promos)} ta):</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(promo_lines)
            + "\n\n<i>(Nusxalash uchun promokod ustiga bosing)</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎟 +5 ta Yangi Yaratish", callback_data="admin_gen_promos")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
        
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ──────────────── KUTILAYOTGAN TO'LOV CHEKLARI ────────────────
@settings_router.callback_query(F.data == "admin_pending_payments")
async def pending_payments_handler(callback: types.CallbackQuery):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    from database import Payment, User
    async with async_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.status == "pending").order_by(Payment.id.desc()).limit(10)
        )
        pending_list = result.scalars().all()
        
    if not pending_list:
        text = "🧾 <b>Ayni damda kutilayotgan to'lov cheklari yo'q.</b>\n\nBarcha to'lovlar ko'rib chiqilgan! ✅"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_pending_payments")],
            [InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    text = f"🧾 <b>KUTILAYOTGAN TO'LOVLAR (Jami: {len(pending_list)} ta):</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for p in pending_list:
        dt_str = p.created_at.strftime("%d.%m %H:%M") if p.created_at else ""
        u_name = f"(@{p.username})" if p.username else ""
        text += (
            f"📌 <b>ID: #{p.id}</b> | <code>{p.user_telegram_id}</code>\n"
            f"👤 Mijoz: <b>{p.user_full_name or 'Noma`lum'}</b> {u_name}\n"
            f"💵 Summa: <b>{p.amount}</b> | Sana: {dt_str}\n"
            f"───────────────────\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{p.id} Tasdiqlash (+30 kun)", callback_data=f"pay_appr_{p.id}"),
            InlineKeyboardButton(text=f"❌ #{p.id} Rad etish", callback_data=f"pay_rejc_{p.id}")
        ])
        
    buttons.append([
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_pending_payments"),
        InlineKeyboardButton(text="🔙 Premium menyusi", callback_data="admin_premium")
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@settings_router.callback_query(F.data.startswith("pay_appr_") | F.data.startswith("pay_rejc_"))
async def process_admin_panel_payment(callback: types.CallbackQuery, bot: Bot):
    if not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
        
    parts = callback.data.split("_")
    action = parts[1]  # "appr" or "rejc"
    payment_id = int(parts[2])
    
    from database import Payment, User
    async with async_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalars().first()
        if not payment:
            await callback.answer("To'lov topilmadi!", show_alert=True)
            return
            
        if payment.status != 'pending':
            await callback.answer(f"Bu to'lov allaqachon ko'rib chiqilgan ({payment.status})!", show_alert=True)
            await pending_payments_handler(callback)
            return
            
        now = datetime.utcnow()
        days = payment.days_granted or 30
        
        if action == "appr":
            payment.status = "approved"
            payment.approved_by = callback.from_user.id
            payment.resolved_at = now
            
            result_user = await session.execute(select(User).where(User.telegram_id == payment.user_telegram_id))
            user = result_user.scalars().first()
            if user:
                if user.is_premium and user.premium_expires_at and user.premium_expires_at > now:
                    user.premium_expires_at += timedelta(days=days)
                else:
                    user.is_premium = True
                    user.premium_expires_at = now + timedelta(days=days)
            await session.commit()
            
            exp_date_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M') if (user and user.premium_expires_at) else "30 kun"
            try:
                kb_user = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚗 Testlarni boshlash", callback_data="testcnt_gai")],
                    [InlineKeyboardButton(text="👑 Bosh menyu", callback_data="back_to_main_menu")]
                ])
                await bot.send_message(
                    payment.user_telegram_id,
                    f"🎉 <b>TABRIKLAYMIZ! TO'LOVINGIZ TASDIQLANDI!</b>\n"
                    f"───────────────────────────\n\n"
                    f"Admin tomonidan to'lovingiz tasdiqlandi va sizga <b>{days} kunlik VIP Premium</b> taqdim etildi.\n"
                    f"⏳ Amal qilish muddati: <b>{exp_date_str} gacha</b>.\n\n"
                    f"👑 <i>Endi barcha VIP imkoniyatlardan cheksiz foydalanishingiz mumkin!</i>",
                    reply_markup=kb_user,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await callback.answer(f"#{payment_id} tasdiqlandi! (+{days} kun VIP berildi)")
        else:
            payment.status = "rejected"
            payment.approved_by = callback.from_user.id
            payment.resolved_at = now
            await session.commit()
            try:
                await bot.send_message(
                    payment.user_telegram_id,
                    "❌ <b>Kechirasiz, siz yuborgan to'lov cheki admin tomonidan tasdiqlanmadi.</b>\n\n"
                    "Savollar bo'yicha @Avto_admin bilan bog'laning.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await callback.answer(f"#{payment_id} rad etildi!")
            
    # Refresh pending payments view
    await pending_payments_handler(callback)
