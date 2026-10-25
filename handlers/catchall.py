from aiogram import Router, types, Bot
from config import ADMIN_IDS
from database import async_session, Setting
from sqlalchemy import select
import logging

catchall_router = Router()

import json
from aiogram import F

@catchall_router.message(F.web_app_data)
async def web_app_data_handler(message: types.Message):
    data_str = message.web_app_data.data
    try:
        data = json.loads(data_str)
        if data.get('action') == 'register':
            full_name = str(data.get('full_name', '')).strip()
            phone = str(data.get('phone', '')).strip()
            language = str(data.get('language', 'uz')).strip()
            region = str(data.get('region', 'Toshkent')).strip()

            from database.models import User, UserStat
            from datetime import datetime, timedelta
            async with async_session() as session:
                result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
                user = result.scalars().first()
                if not user:
                    user = User(
                        telegram_id=message.from_user.id,
                        full_name=full_name,
                        phone=phone,
                        language=language,
                        region=region,
                        is_premium=True,
                        premium_expires_at=datetime.utcnow() + timedelta(days=5),
                        points=50
                    )
                    session.add(user)
                    await session.flush()
                    user_stat = UserStat(user_id=user.id)
                    session.add(user_stat)
                else:
                    user.full_name = full_name
                    user.phone = phone
                    user.language = language
                    user.region = region
                    if not user.is_premium or (user.premium_expires_at and user.premium_expires_at < datetime.utcnow()):
                        user.is_premium = True
                        user.premium_expires_at = datetime.utcnow() + timedelta(days=5)
                await session.commit()

            await message.answer(
                f"🎉 <b>XUSH KELIBSIZ, {full_name.upper()}!</b>\n\n"
                f"✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n"
                f"🎁 Sizga <b>5 kunlik VIP Premium</b> va <b>+50 ball</b> sovg'a qilindi!",
                parse_mode="HTML"
            )

        elif data.get('action') == 'test_completed':
            correct = data.get('correct', 0)
            total = data.get('total', 10)
            
            async with async_session() as session:
                from database.models import User, UserStat
                result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
                user = result.scalars().first()
                
                if user:
                    added_points = correct * 5
                    user.points += added_points
                    
                    stat_result = await session.execute(select(UserStat).where(UserStat.user_id == user.id))
                    user_stat = stat_result.scalars().first()
                    
                    if user_stat:
                        user_stat.tests_taken += 1
                        user_stat.correct_answers += correct
                        user_stat.wrong_answers += (total - correct)
                    
                    await session.commit()
                    await message.answer(
                        f"🎉 **Test muvaffaqiyatli yakunlandi!**\n\n"
                        f"✅ To'g'ri javoblar: {correct}/{total}\n"
                        f"🏆 Sizga {added_points} ball berildi!"
                    )
    except Exception as e:
        logging.error(f"WebApp data error: {e}")

from aiogram.fsm.context import FSMContext

@catchall_router.message()
async def forward_user_messages(message: types.Message, state: FSMContext):
    # Agar xabar admindan bo'lsa yoki guruhda bo'lsa, forward qilmaymiz
    if message.from_user.id in ADMIN_IDS or message.chat.type != "private":
        return
        
    # Noto'g'ri tugma yoki yozuv kelsa, holatni tozalaymiz
    await state.clear()
    
    # Asosiy menyuni chaqirish uchun start bosishni eslatamiz
    await message.answer("Tushunarsiz buyruq yoki xabar. Iltimos, pastdagi menyudan kerakli bo'limni tanlang yoki /start ni bosing.")
    
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key == "forward_status"))
        setting = result.scalars().first()
        
    if setting and setting.value == "1":
        try:
            # Xabarni barcha adminlarga yuborish
            for admin_id in ADMIN_IDS:
                try:
                    await message.forward(chat_id=admin_id)
                except Exception as e:
                    logging.error(f"Adminga ({admin_id}) xabar uzatishda xatolik: {e}")
        except Exception as e:
            logging.error(f"Xabarni uzatishda umumiy xatolik: {e}")
