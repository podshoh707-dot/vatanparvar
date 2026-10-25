from aiogram import Router, types, F, Bot
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from database import async_session, Setting, User, Payment, PromoCode
from sqlalchemy import select
from config import ADMIN_IDS
from utils.permissions import check_permission
import logging

premium_router = Router()

class PremiumStates(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_promocode = State()


@premium_router.message(F.text.in_([
    "💎 VIP (Premium)", "💎 VIP", "💎 VIP (Premium xarid qilish)", "💎 VIP Premium", "💎 Premium", "⭐ Premium"
]))
async def premium_menu(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
        
    async with async_session() as session:
        # User holatini olish
        result_user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result_user.scalars().first()
        
        now = datetime.utcnow()
        # Premium status tekshiruvi va 30 kunlik reja tugagan bo'lsa avtomatik yopish
        if user:
            if user.is_premium:
                if user.premium_expires_at and user.premium_expires_at > now:
                    days_left = (user.premium_expires_at - now).days
                    exp_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M')
                    status_text = f"🟢 <b>VIP Obuna Faol</b> (Qolgan vaqt: {days_left} kun)\n⏳ Tugash sanasi: <b>{exp_str}</b>"
                else:
                    # 30 kunlik muddat tugagan — rejani avtomatik yopamiz
                    user.is_premium = False
                    await session.commit()
                    status_text = "🔴 <b>VIP Obuna Faol Emas (30 kunlik muddat tugagan)</b>"
            else:
                status_text = "🔴 <b>VIP Obuna Faol Emas</b>"
        else:
            status_text = "🔴 <b>VIP Obuna Faol Emas</b>"

        # Tarif matni va narxini olish
        result_text = await session.execute(select(Setting).where(Setting.key == "tariff_text"))
        text_setting = result_text.scalars().first()
        
        result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        price_setting = result_price.scalars().first()
        
        tariff_text = text_setting.value if text_setting and text_setting.value else (
            "🚀 <b>VIP Premium Afzalliklari:</b>\n"
            " • 👑 <b>GAI Imtihon Simulyatori:</b> 20 ta savol + Rasmiy Nomli Oltin Sertifikat\n"
            " • 🎯 <b>Xatolar Tahlili:</b> Barcha noto'g'ri ishlangan savollar ustida ishlash\n"
            " • 📚 <b>Cheksiz Testlar:</b> Kunlik va oylik cheklovlarsiz barcha testlar\n"
            " • ⚡️ <b>Tezkor Yechim:</b> Har bir savol ostida rasmiy YHQ izohi va qoidasi\n"
            " • 🚫 <b>Reklamasiz Tizim:</b> Mutlaqo reklamasiz toza va tezkor interfeys"
        )
        
        tariff_price = price_setting.value if price_setting and price_setting.value else "50 000 so'm / oy"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 To'lov Usullari ({tariff_price})", callback_data="premium_buy")],
        [InlineKeyboardButton(text="⭐ Telegram Stars orqali (Darhol)", callback_data="premium_stars")],
        [InlineKeyboardButton(text="🎟 Promokod kiritish", callback_data="premium_promo")],
        [InlineKeyboardButton(text="🎁 Hamkorlik va Avtomaktablar", callback_data="premium_partner")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="back_to_main_menu")]
    ])
    
    text = (
        f"👑 <b>VIP PREMIUM OBUNA MARKAZI</b>\n"
        f"───────────────────────────\n\n"
        f"👤 <b>Sizning holatingiz:</b>\n{status_text}\n\n"
        f"───────────────────────────\n"
        f"{tariff_text}\n\n"
        f"💳 <b>Obuna narxi:</b> <code>{tariff_price}</code>"
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@premium_router.callback_query(F.data.startswith("premium_"))
async def handle_premium_action(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    action = callback.data.split("_")[1]
    
    if action == "buy":
        async with async_session() as session:
            result_mode = await session.execute(select(Setting).where(Setting.key == "premium_mode"))
            mode_setting = result_mode.scalars().first()
            if mode_setting and mode_setting.value == "0":
                await callback.message.edit_text("⚠️ Hozirda Premium obunalar xaridi vaqtincha to'xtatilgan.")
                return
                
            result_card = await session.execute(select(Setting).where(Setting.key == "admin_card"))
            card_setting = result_card.scalars().first()
            card_num = card_setting.value if card_setting and card_setting.value else "8600 0000 0000 0000"
            
            result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
            price_setting = result_price.scalars().first()
            tariff_price = price_setting.value if price_setting and price_setting.value else "50 000 so'm"
            
        pay_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Click orqali to'lov", url="https://my.click.uz/")],
            [InlineKeyboardButton(text="📲 Payme orqali to'lov", url="https://payme.uz/")],
            [InlineKeyboardButton(text="📥 Chekni yuborish (Skrinshot)", callback_data="premium_send")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back")]
        ])
            
        text = (
            f"💎 <b>VIP PREMIUM OBUNA TO'LOVI (30 KUN)</b>\n"
            f"───────────────────────────\n\n"
            f"💰 <b>To'lov summasi:</b> <code>{tariff_price}</code>\n"
            f"💳 <b>Karta raqami:</b> <code>{card_num}</code>\n"
            f"<i>(Karta raqamini nusxalash uchun ustiga bosing)</i>\n\n"
            f"───────────────────────────\n"
            f"📌 <b>To'lov tartibi:</b>\n"
            f"1. Click, Payme yoki bank ilovasi orqali to'lovni bajaring.\n"
            f"2. Pastdagi <b>📥 Chekni yuborish</b> tugmasini bosib to'lov skrinshotini yuboring.\n"
            f"3. Admin tekshirishi bilan VIP 30 kunga profilingizda avtomatik faollashadi."
        )
        await callback.message.edit_text(text, reply_markup=pay_kb, parse_mode="HTML")
        
    elif action == "send":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="premium_cancel")]
        ])
        await callback.message.edit_text(
            "📥 <b>To'lov chekini yuboring:</b>\n\n"
            "Iltimos, to'lov muvaffaqiyatli o'tganini tasdiqlovchi chek skrinshotini ushbu chatga rasm ko'rinishida yuboring:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await state.set_state(PremiumStates.waiting_for_receipt)

    elif action == "stars":
        # Telegram Stars to'lovi (150 Stars ~ 30 kunlik VIP)
        prices = [LabeledPrice(label="VIP Premium (30 kunlik)", amount=150)]
        try:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title="VIP Premium Obuna (30 kun)",
                description="Avtomaktab platformasida cheksiz testlar, GAI imtihoni simulyatori, xatolar tahlili va sertifikat olish imkoniyati.",
                payload=f"stars_vip_{callback.from_user.id}",
                currency="XTR",
                prices=prices,
                provider_token="" # Telegram Stars uchun provider_token bo'sh qoldiriladi
            )
        except Exception as e:
            await callback.message.answer(f"Stars to'lovida xatolik: {e}")

    elif action == "promo":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="premium_cancel")]
        ])
        await callback.message.edit_text(
            "🎟 <b>Promokod kiritish:</b>\n\n"
            "Maxsus promokodingizni ushbu chatga yozib yuboring (Masalan: <code>VIP-ABC123</code>):",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await state.set_state(PremiumStates.waiting_for_promocode)
        
    elif action == "cancel":
        await state.clear()
        await callback.answer("Bekor qilindi")
        await premium_menu(callback.message, state)
        return

    elif action == "partner":
        text = (
            "🎁 <b>AVTOMAKTABLAR VA HAMKORLAR UCHUN</b>\n"
            "───────────────────────────\n\n"
            "Avtomaktabingiz o'quvchilari uchun ommaviy VIP obunalar, maxsus integratsiya va chegirmalar mavjud.\n\n"
            "📞 Aloqa markazi va hamkorlik:\n"
            "👤 <b>Telegram:</b> @Avto_admin\n"
            "📱 <b>Telefon:</b> +998 97 069 70 77"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Adminga yozish", url="https://t.me/Avto_admin")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        
    elif action == "back":
        await premium_menu(callback.message, state)
        
    await callback.answer()


# Pre-checkout query handler for Telegram Stars
@premium_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


# Successful Stars Payment
@premium_router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    sp = message.successful_payment
    total_amount = sp.total_amount if sp else 150
    currency = sp.currency if sp else "XTR"
    
    async with async_session() as session:
        result_user = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result_user.scalars().first()
        if not user:
            user = User(
                telegram_id=user_id,
                full_name=message.from_user.full_name,
                language="uz"
            )
            session.add(user)
            await session.flush()
            
        now = datetime.utcnow()
        if user.is_premium and user.premium_expires_at and user.premium_expires_at > now:
            user.premium_expires_at += timedelta(days=30)
        else:
            user.is_premium = True
            user.premium_expires_at = now + timedelta(days=30)
            
        # Bazaga to'lov yozuvini kiritamiz
        payment = Payment(
            user_telegram_id=user_id,
            user_full_name=message.from_user.full_name,
            username=message.from_user.username,
            amount=f"{total_amount} {currency} (Stars)",
            status='approved',
            days_granted=30,
            resolved_at=now
        )
        session.add(payment)
        await session.commit()
        exp_date_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M')

    # Adminlarga bildirishnoma yuborish
    admin_notif = (
        f"⭐️ <b>YANGI TELEGRAM STARS TO'LOVI!</b>\n"
        f"───────────────────────────\n\n"
        f"👤 <b>Mijoz:</b> {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Summa:</b> {total_amount} {currency} (Telegram Stars)\n"
        f"✅ <b>Holat:</b> +30 kunlik VIP Premium avtomatik faollashtirildi!\n"
        f"⏳ <b>Amal qilish muddati:</b> {exp_date_str}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_notif, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Stars to'lovi haqida adminga xabar yuborishda xatolik: {e}")

    kb_success = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Testlarni boshlash", callback_data="testcnt_gai")],
        [InlineKeyboardButton(text="👑 Bosh menyu", callback_data="back_to_main_menu")]
    ])

    await message.answer(
        f"🎉 <b>TO'LOVINGIZ QABUL QILINDI!</b>\n"
        f"───────────────────────────\n\n"
        f"⭐️ Telegram Stars to'lovi muvaffaqiyatli qabul qilindi!\n"
        f"👑 Sizga <b>30 kunlik VIP Premium</b> faollashtirildi.\n"
        f"⏳ <b>Amal qilish muddati:</b> <b>{exp_date_str} gacha</b>.\n\n"
        f"🚀 <i>Endi GAI imtihoni simulyatori, xatolar tahlili, rasmiy sertifikat va barcha testlardan cheksiz foydalanishingiz mumkin!</i>",
        reply_markup=kb_success,
        parse_mode="HTML"
    )


# Promokod tekshirish
@premium_router.message(PremiumStates.waiting_for_promocode)
async def process_promocode(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    
    # Bekor qilish yoki bosh menyuga qaytish
    if text.startswith("/") or text in ["🔙 Bekor qilish", "🏠 Bosh menyu", "🚗 Test ishlash", "💎 VIP (Premium)", "📊 Statistika"]:
        await state.clear()
        await message.answer("Promokod kiritish bekor qilindi.")
        return
        
    code = text.upper()
    async with async_session() as session:
        result_code = await session.execute(
            select(PromoCode).where(PromoCode.code == code, PromoCode.is_active == True)
        )
        promo = result_code.scalars().first()
        if not promo:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="premium_cancel")]
            ])
            await message.answer(
                "❌ <b>Noto'g'ri yoki allaqachon ishlatilgan promokod!</b>\n\n"
                "Iltimos, qaytadan tekshirib yozing yoki bekor qiling:",
                reply_markup=kb,
                parse_mode="HTML"
            )
            return
            
        result_user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result_user.scalars().first()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                full_name=message.from_user.full_name,
                language="uz"
            )
            session.add(user)
            await session.flush()
            
        days = promo.days_granted or 30
        now = datetime.utcnow()
        if user.is_premium and user.premium_expires_at and user.premium_expires_at > now:
            user.premium_expires_at += timedelta(days=days)
        else:
            user.is_premium = True
            user.premium_expires_at = now + timedelta(days=days)
        
        # Promokodni ishlatilgan deb belgilash
        promo.is_active = False
        
        # To'lovlar ro'yxatiga ham qayd qilish
        payment = Payment(
            user_telegram_id=user.telegram_id,
            user_full_name=message.from_user.full_name,
            username=message.from_user.username,
            amount=f"Promokod ({code})",
            status="approved",
            days_granted=days,
            resolved_at=now
        )
        session.add(payment)
        await session.commit()
        exp_date_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M')

    await state.clear()
    kb_success = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Testlarni boshlash", callback_data="testcnt_gai")],
        [InlineKeyboardButton(text="👑 Bosh menyu", callback_data="back_to_main_menu")]
    ])
    
    await message.answer(
        f"🎉 <b>TABRIKLAYMIZ! PROMOKOD FAOLLASHTIRILDI!</b>\n"
        f"───────────────────────────\n\n"
        f"🎁 Sizga <b>+{days} kun VIP Premium</b> muvaffaqiyatli taqdim etildi!\n"
        f"⏳ <b>Yangi amal qilish muddati:</b> <b>{exp_date_str} gacha</b>.\n\n"
        f"🚀 <i>Endi barcha maxsus testlar, GAI imtihoni simulyatori va xatolar tahlilidan cheksiz foydalanishingiz mumkin!</i>",
        reply_markup=kb_success,
        parse_mode="HTML"
    )


# Chek qabul qilish (rasm)
@premium_router.message(PremiumStates.waiting_for_receipt, F.photo)
async def process_receipt(message: types.Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = message.from_user.username or "Noma'lum"
    
    # Tarif narxini olish
    async with async_session() as session:
        result_price = await session.execute(select(Setting).where(Setting.key == "tariff_price"))
        price_setting = result_price.scalars().first()
        tariff_price = price_setting.value if price_setting and price_setting.value else "50 000 so'm"
        
        # Payment yozuvini yaratish
        payment = Payment(
            user_telegram_id=user_id,
            user_full_name=message.from_user.full_name,
            username=username,
            amount=tariff_price,
            status='pending',
            days_granted=30
        )
        session.add(payment)
        await session.commit()
        payment_id = payment.id
    
    # Adminga yuborish
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash (+30 kun)", callback_data=f"approve_prem_{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_prem_{payment_id}")
        ]
    ])
    
    admin_msg = (
        f"💸 <b>YANGI PREMIUM TO'LOV CHEKI!</b>\n\n"
        f"📌 <b>ID:</b> #{payment_id}\n"
        f"👤 <b>Mijoz:</b> {message.from_user.full_name} (@{username})\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Summa:</b> <code>{tariff_price}</code>\n"
        f"⏳ <b>Muddat:</b> 30 kunlik VIP\n\n"
        f"Tasdiqlaysizmi?"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=admin_msg, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Adminga to'lovni yuborishda xatolik: {e}")
            
    await message.answer(
        "✅ <b>To'lov chekingiz adminga muvaffaqiyatli yuborildi!</b>\n\n"
        "Admin tekshirib tasdiqlashi bilan profilingizda 30 kunlik VIP Premium faollashadi va sizga bildirishnoma yuboriladi.",
        parse_mode="HTML"
    )
    await state.clear()


@premium_router.message(PremiumStates.waiting_for_receipt)
async def receipt_error(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if text.startswith("/") or text in ["🔙 Bekor qilish", "🏠 Bosh menyu", "🚗 Test ishlash"]:
        await state.clear()
        await message.answer("Chek yuborish bekor qilindi.")
        return
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="premium_cancel")]
    ])
    await message.answer(
        "⚠️ <b>Iltimos, to'lov chekini rasm (skrinshot) ko'rinishida yuboring.</b>\n\nYoki pastdagi tugma orqali bekor qiling:",
        reply_markup=kb,
        parse_mode="HTML"
    )


# Admin xabardagi to'g'ridan-to'g'ri Tasdiqlash / Rad etish Callback Handler
@premium_router.callback_query(F.data.startswith("approve_prem_") | F.data.startswith("reject_prem_"))
async def admin_premium_action(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS and not await check_permission(callback.from_user.id, "can_manage_premium"):
        await callback.answer("Sizda to'lovlarni boshqarish huquqi yo'q!", show_alert=True)
        return
        
    action, _, payment_id_str = callback.data.split("_")
    payment_id = int(payment_id_str)
    
    async with async_session() as session:
        result_payment = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result_payment.scalars().first()
        
        if not payment:
            await callback.answer("To'lov ma'lumotlari topilmadi!", show_alert=True)
            return
            
        if payment.status != 'pending':
            await callback.answer(f"Bu to'lov allaqachon ko'rib chiqilgan ({payment.status})!", show_alert=True)
            return
            
        target_user_id = payment.user_telegram_id
        now = datetime.utcnow()
        days = payment.days_granted or 30
        
        if action == "approve":
            result_user = await session.execute(select(User).where(User.telegram_id == target_user_id))
            user = result_user.scalars().first()
            if user:
                if user.is_premium and user.premium_expires_at and user.premium_expires_at > now:
                    user.premium_expires_at += timedelta(days=days)
                else:
                    user.is_premium = True
                    user.premium_expires_at = now + timedelta(days=days)
                
            payment.status = 'approved'
            payment.approved_by = callback.from_user.id
            payment.resolved_at = now
            await session.commit()
            
            exp_date_str = user.premium_expires_at.strftime('%d.%m.%Y %H:%M') if user and user.premium_expires_at else "30 kun"
            
            try:
                kb_user = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚗 Testlarni boshlash", callback_data="testcnt_gai")],
                    [InlineKeyboardButton(text="👑 Bosh menyu", callback_data="back_to_main_menu")]
                ])
                await bot.send_message(
                    target_user_id, 
                    f"🎉 <b>TABRIKLAYMIZ! TO'LOVINGIZ TASDIQLANDI!</b>\n"
                    f"───────────────────────────\n\n"
                    f"To'lov chekingiz admin tomonidan tasdiqlandi va sizga <b>{days} kunlik VIP Premium</b> taqdim etildi.\n"
                    f"⏳ Amal qilish muddati: <b>{exp_date_str} gacha</b>.\n\n"
                    f"👑 <i>Endi GAI Imtihoni, Xatolar tahlili va sertifikat olish imkoniyatlaridan bemalol foydalanishingiz mumkin!</i>",
                    reply_markup=kb_user,
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + f"\n\n✅ <b>TASDIQLANDI (+{days} KUN VIP)</b>\nAdmin: <code>{callback.from_user.id}</code>",
                parse_mode="HTML"
            )
        else:
            payment.status = 'rejected'
            payment.approved_by = callback.from_user.id
            payment.resolved_at = now
            await session.commit()
            
            try:
                await bot.send_message(
                    target_user_id, 
                    "❌ <b>Kechirasiz, siz yuborgan to'lov cheki tasdiqlanmadi.</b>\n\n"
                    "Chek noto'g'ri yuborilgan yoki mablag' kelib tushmagan bo'lishi mumkin.\n"
                    "Savollar bo'yicha @Avto_admin bilan bog'laning.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            await callback.message.edit_caption(
                caption=(callback.message.caption or "") + f"\n\n❌ <b>RAD ETILDI</b>\nAdmin: <code>{callback.from_user.id}</code>",
                parse_mode="HTML"
            )
        
    await callback.answer("Mijozga xabar yuborildi!")
