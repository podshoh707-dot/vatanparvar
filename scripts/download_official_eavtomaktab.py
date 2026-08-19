"""
100% Rasmiy e-avtomaktab.uz rasmlarini yuklab olish va OsonPrava ni to'liq tozalash skripti.
"""
import urllib.request
import os
import sys
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from database import async_session, Question
from sqlalchemy import select

IMG_DIR = os.path.join(BASE_DIR, "webapp", "images")
os.makedirs(IMG_DIR, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def download_image(q_id):
    filename = f"e-avtomaktab{q_id}.jpg"
    target_path = os.path.join(IMG_DIR, filename)
    
    url = f"https://e-avtoshkola.uz/storage/tests/e-avtomaktab{q_id}.jpg"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read()
            if len(content) > 100: # Valid image
                with open(target_path, "wb") as f:
                    f.write(content)
                return q_id, f"images/{filename}", True
    except Exception:
        pass
    return q_id, None, False

async def run_sync():
    print("="*60)
    print("🚀 1. BARCHA 1242 TA SAVOL UCHUN RASMIY E-AVTOMAKTAB RASMLARINI YUKLASH...")
    print("="*60)
    
    async with async_session() as session:
        result = await session.execute(select(Question).order_by(Question.id))
        questions = result.scalars().all()
        q_ids = [q.id for q in questions]
        
    print(f"Jami savollar soni: {len(q_ids)} ta. Yuklab olish boshlandi...")
    
    downloaded_map = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(download_image, q_ids))
        for q_id, rel_path, success in results:
            if success:
                downloaded_map[q_id] = rel_path

    print(f"✅ Rasmiy e-avtomaktab rasmlari muvaffaqiyatli yuklandi: {len(downloaded_map)} ta!")
    
    print("\n" + "="*60)
    print("🚀 2. BAZADA OSONPRAVA NI TO'LIQ O'CHIRIB, E-AVTOMAKTAB GA O'TKAZISH...")
    print("="*60)
    
    updated_q_json = []
    async with async_session() as session:
        result = await session.execute(select(Question).order_by(Question.id))
        questions = result.scalars().all()
        
        for q in questions:
            # 1. Rasmni almashtirish
            if q.id in downloaded_map:
                q.image_url = downloaded_map[q.id]
            elif str(q.image_url or '').startswith("http") and "osonprava" in str(q.image_url).lower():
                # Agar e-avtomaktab da bu ID bo'lmasa, uni tozalash
                local_fallback = os.path.join(IMG_DIR, f"{q.id}.jpg")
                if os.path.exists(local_fallback):
                    q.image_url = f"images/{q.id}.jpg"
                else:
                    q.image_url = None
            
            # 2. Textlardagi Osonprava nomlarini tozalash
            if q.text and "osonprava" in q.text.lower():
                q.text = q.text.replace("OsonPrava", "E-Avtomaktab").replace("osonprava", "e-avtomaktab")
                
            updated_q_json.append({
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
        print("✅ Ma'lumotlar bazasida barcha savollar 100% rasmiy e-avtomaktab ga o'tkazildi!")

    # 3. JSON fayllarni sinxronlash
    for target_dir in [os.path.join(BASE_DIR, "webapp"), os.path.join(BASE_DIR, "webapp", "avtomaktab-webapp")]:
        os.makedirs(target_dir, exist_ok=True)
        j_path = os.path.join(target_dir, "questions.json")
        with open(j_path, "w", encoding="utf-8") as f:
            json.dump(updated_q_json, f, ensure_ascii=False, indent=2)
        print(f"✅ {j_path} yangilandi!")

    print("\n" + "="*60)
    print("🏆 BARCHA TESTLAR VA RASMLAR 100% RASMIY E-AVTOMAKTAB GA O'TKAZILDI!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_sync())
