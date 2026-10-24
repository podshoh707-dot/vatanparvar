import json
import sqlite3
import re

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()
cur.execute("SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation FROM questions WHERE image_url IS NOT NULL ORDER BY id")
rows = cur.fetchall()
print(f"Total questions with image_url in DB: {len(rows)}")

# Let's write an analysis for all questions with image_url
results = []
for r in rows:
    qid, cat, text, img, oa, ob, oc, od, corr, exp = r
    t_lower = text.lower()
    
    # Check what kind of question it is
    is_pure_text = False
    reason = ""
    
    # 1. First Aid
    if any(w in t_lower for w in ['tibbiy', 'yordam', 'lat yeganda', 'singanda', 'qon ketganda', 'jgut', 'bint', 'nafas', 'jarohat']):
        is_pure_text = True
        reason = "Birinchi tibbiy yordam (rasm kerak emas)"
    # 2. Documents / Law / Fines
    elif any(w in t_lower for w in ['guvohnoma', 'hujjat', 'jarima', 'javobgarlik', 'sug\'urta', 'ishonchnoma']):
        is_pure_text = True
        reason = "Hujjatlar va qonunchilik (rasm kerak emas)"
    # 3. Headlights / Signals in text without sign
    elif any(w in t_lower for w in ['yaqinni yorituvchi', 'uzoqni yorituvchi', 'fara chirog', 'fara', 'ogohlantirish ishorasi bo\'ladimi', 'tovushli ishora']):
        if not any(w in t_lower for w in ['belgi', 'chiziq', 'svetofor', 'chorraha']):
            is_pure_text = True
            reason = "Chiroqlar va ishoralar nazariy qoidasi (rasm kerak emas)"
    # 4. Physics / Road safety fundamentals
    elif any(w in t_lower for w in ['tortish kuchi', 'tishlashish kuchi', 'sirpanish', 'markazdan qochma', 'tormoz yo\'li', 'inersiya']):
        is_pure_text = True
        reason = "Harakat xavfsizligi fizikasi (rasm kerak emas)"
    # 5. Definitions / Terms
    elif any(w in t_lower for w in ['atamasi nimani bildiradi', 'atamasi qanday ma\'no', 'kimlar "yo\'l harakati qatnashchisi"', 'tushuniladi']):
        is_pure_text = True
        reason = "YHQ atamalari va ta'riflar (rasm kerak emas)"
    # 6. Passenger / Pedestrian pure text rules
    elif any(w in t_lower for w in ['piyodalarning majburiyat', 'yo\'lovchilarning majburiyat', 'haydovchining majburiyat']):
        if not any(w in t_lower for w in ['belgi', 'chiziq', 'svetofor', 'chorraha', 'rasm']):
            is_pure_text = True
            reason = "Majburiyatlar nazariyasi (rasm kerak emas)"
    # 7. Technical defects
    elif any(w in t_lower for w in ['shina protektor', 'naqshlarining balandligi', 'rul chambagi', 'lyuft', 'tormoz tizimi nosoz']):
        if not any(w in t_lower for w in ['belgi', 'chiziq', 'surat', 'rasm']):
            is_pure_text = True
            reason = "Texnik holat nazariyasi (rasm kerak emas)"
    # 8. Shatakka olish / towing numbers
    elif any(w in t_lower for w in ['egiluvchan ulagich', 'qattiq ulagich']) and not any(w in t_lower for w in ['belgi', 'surat', 'rasm']):
        is_pure_text = True
        reason = "Shatakka olish nazariyasi (rasm kerak emas)"

    results.append({
        "id": qid,
        "category": cat,
        "text": text,
        "image_url": img,
        "is_pure_text": is_pure_text,
        "reason": reason
    })

pure_count = sum(1 for r in results if r["is_pure_text"])
print(f"Definite pure-text questions having wrong image: {pure_count}")

with open("scratch/audit_mismatched_images.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("Saved scratch/audit_mismatched_images.json")
con.close()
