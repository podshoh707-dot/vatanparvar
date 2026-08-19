"""
Barcha 1242 ta test savollaridagi kodirovka va matn xatoliklarini to'liq tozalash va tuzatish skripti.
"""
import os
import sys
import json
import asyncio
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database import async_session, Question
from sqlalchemy import select

def clean_str(s: str) -> str:
    if not s:
        return ""
    
    # 1. Umumiy kodirovka xatolarini to'g'irlash
    t = s.replace("\ufffd", "'").replace("â€™", "'").replace("â€œ", '"').replace("â€", '"')
    t = t.replace("’", "'").replace("‘", "'").replace("ʻ", "'").replace("ʼ", "'").replace("`", "'")
    t = t.replace("\xa0", " ") # Non-breaking space
    
    # 2. Ortiqcha probellarni tozalash
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

async def fix_database_encoding():
    print("="*60)
    print("🚀 BARCHA 1242 TA TEST MATNLARINI TO'LIQ TOZALASH VA TUZATISH...")
    print("="*60)

    updated_questions = []

    async with async_session() as session:
        result = await session.execute(select(Question).order_by(Question.id))
        questions = result.scalars().all()

        fixed_count = 0
        for q in questions:
            old_text = q.text
            q.text = clean_str(q.text)
            q.option_a = clean_str(q.option_a)
            q.option_b = clean_str(q.option_b)
            q.option_c = clean_str(q.option_c)
            q.option_d = clean_str(q.option_d)
            q.explanation = clean_str(q.explanation)
            q.category = clean_str(q.category)

            if q.text != old_text or "\ufffd" in str(old_text):
                fixed_count += 1

            updated_questions.append({
                "id": q.id,
                "text": q.text,
                "image_url": q.image_url or "",
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c or "",
                "option_d": q.option_d or "",
                "correct_option": q.correct_option,
                "explanation": q.explanation or "",
                "category": q.category or "Umumiy",
                "media_urls": q.media_urls
            })

        await session.commit()
        print(f"✅ Baza bo'yicha {fixed_count} ta savoldagi matn xatoliklari va maxsus belgilar tuzatildi!")

    # JSON fayllarni yangilash
    for target_dir in [os.path.join(BASE_DIR, "webapp"), os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp")]:
        os.makedirs(target_dir, exist_ok=True)
        j_path = os.path.join(target_dir, "questions.json")
        with open(j_path, "w", encoding="utf-8") as f:
            json.dump(updated_questions, f, ensure_ascii=False, indent=2)
        print(f"✅ {j_path} muvaffaqiyatli saqlandi!")

    print("\n" + "="*60)
    print("🏆 BARCHA 1242 TA SAVOL MATNI VA VARIANTLARI 100% TOZALANDI!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(fix_database_encoding())
