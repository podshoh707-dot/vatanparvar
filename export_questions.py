"""
Bu skript bazadan savollarni olib webapp/questions.json va webapp/avtomaktab-webapp/questions.json fayllariga yozadi.
Ishga tushirish: python export_questions.py
Keyin questions.json faylini GitHub'ga yuklang — GitHub Pages avtomatik yangilanadi.
"""
import asyncio
import json
import os
import sys

# Loyiha papkasiga o'tamiz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import async_session, Question
from sqlalchemy import select

async def export():
    output_path1 = os.path.join(os.path.dirname(__file__), "webapp", "questions.json")
    output_path2 = os.path.join(os.path.dirname(__file__), "webapp", "avtomaktab-webapp", "questions.json")
    
    async with async_session() as session:
        result = await session.execute(select(Question))
        questions = result.scalars().all()
    
    data = []
    for q in questions:
        image_url = None
        if q.image_url:
            if str(q.image_url).startswith("http"):
                image_url = q.image_url
            else:
                base_name = os.path.basename(str(q.image_url))
                image_url = f"images/{base_name}"
        
        options = [
            {"letter": "A", "text": q.option_a},
        ]
        if q.option_b:
            options.append({"letter": "B", "text": q.option_b})
        if q.option_c:
            options.append({"letter": "C", "text": q.option_c})
        if q.option_d:
            options.append({"letter": "D", "text": q.option_d})
        
        data.append({
            "id": q.id,
            "text": q.text,
            "image_url": image_url,
            "options": options,
            "correct": q.correct_option,
            "explanation": q.explanation or "",
            "category": q.category or "Umumiy",
            "difficulty": q.difficulty or "o'rta"
        })
    
    with open(output_path1, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if os.path.exists(os.path.dirname(output_path2)):
        with open(output_path2, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"OK: {len(data)} ta savol eksport qilindi!")
    print(f"   1) {output_path1}")
    print(f"   2) {output_path2}")

if __name__ == "__main__":
    asyncio.run(export())
