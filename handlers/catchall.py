from aiogram import Router, types, Bot
from config import ADMIN_IDS
from database import async_session, Setting
from sqlalchemy import select
import logging

catchall_router = Router()

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
