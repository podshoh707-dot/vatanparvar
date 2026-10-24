from aiogram import Router, types, F
from database import async_session, Question
from sqlalchemy import select

channel_quiz_router = Router()

@channel_quiz_router.callback_query(F.data.startswith("ch_ans_"))
async def process_channel_answer(callback: types.CallbackQuery):
    # Format: ch_ans_{qid}_{ans}
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return
        
    qid = int(parts[1])
    ans = parts[2]
    
    async with async_session() as session:
        result = await session.execute(select(Question).where(Question.id == qid))
        q = result.scalars().first()
        
    if not q:
        await callback.answer("Bu savol bazadan topilmadi.", show_alert=True)
        return
        
    corr_option = str(q.correct_option or "").strip().upper()
    user_ans = str(ans or "").strip().upper()
    
    options_map = {
        "A": q.option_a or "",
        "B": q.option_b or "",
        "C": q.option_c or "",
        "D": q.option_d or ""
    }
    
    correct_text = options_map.get(corr_option, "")
    
    if user_ans == corr_option:
        msg = f"✅ To'g'ri javob!\nSizning javobingiz: {user_ans}) {correct_text}"
        if q.explanation:
            msg += f"\n\n📖 Izoh: {q.explanation}"
        if len(msg) > 195:
            msg = msg[:195] + "..."
        await callback.answer(msg, show_alert=True)
    else:
        chosen_text = options_map.get(user_ans, "")
        msg = (
            f"❌ Noto'g'ri!\n"
            f"Siz tanladingiz: {user_ans}) {chosen_text}\n\n"
            f"✅ To'g'ri javob: {corr_option}) {correct_text}"
        )
        if q.explanation:
            msg += f"\n\n📖 Izoh: {q.explanation}"
        
        # Max length for callback answer is 200 chars. We might need to trim it.
        if len(msg) > 195:
            msg = msg[:195] + "..."
            
        await callback.answer(msg, show_alert=True)

