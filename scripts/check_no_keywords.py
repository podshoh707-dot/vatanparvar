import json
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation 
    FROM questions 
    WHERE image_url IS NOT NULL 
    ORDER BY id
""")
rows = cur.fetchall()

keywords = [
    'belgi', 'chiziq', 'svetofor', 'chorraha', 'yo\'naltirgich', 'tartibga soluvchi',
    'tartibda o\'tadilar', 'tartibda o‘tadilar', 'birinchi bo\'lib o\'tadi', 'birinchi bo‘lib o‘tadi',
    'oxirgi bo\'lib o\'tadi', 'oxirgi bo‘lib o‘tadi', 'yo\'l berishi kerak', 'yoʻl berishi kerak',
    'harakatlanish huquqiga ega', 'harakatlanish ruxsat etiladi', 'harakatlanishga ruxsat etiladi',
    'harakatlanish taqiqlanadi', 'quvib o\'tishga ruxsat', 'quvib o‘tishga ruxsat',
    'to\'xtashga ruxsat', 'toʻxtashga ruxsat', 'to\'xtab turishga ruxsat', 'toʻxtab turishga ruxsat',
    'shu joyda', 'ushbu holatda', 'mazkur holatda', 'ko\'rsatilgan holatda', 'koʻrsatilgan holatda',
    'ko\'rsatilgan vaziyatda', 'koʻrsatilgan vaziyatda', 'suratda', 'rasmda', 'yo\'nalishlarda harakatlanishga ruxsat'
]

no_keyword_qs = []
with_keyword_qs = []

for r in rows:
    qid, cat, text, img, oa, ob, oc, od, corr, exp = r
    t_low = text.lower()
    matched_kw = [k for k in keywords if k in t_low]
    if not matched_kw:
        no_keyword_qs.append({
            "id": qid, "category": cat, "text": text, "image_url": img,
            "option_a": oa, "option_b": ob, "option_c": oc, "option_d": od,
            "correct_option": corr, "explanation": exp
        })
    else:
        with_keyword_qs.append(qid)

print(f"Total with images: {len(rows)}")
print(f"Questions without visual/situational keywords: {len(no_keyword_qs)}")

with open("scratch/questions_no_keywords.json", "w", encoding="utf-8") as f:
    json.dump(no_keyword_qs, f, ensure_ascii=False, indent=2)

print("Saved scratch/questions_no_keywords.json")
con.close()
