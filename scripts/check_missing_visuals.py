import json
import sqlite3
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, option_a, option_b, option_c, option_d, correct_option, explanation 
    FROM questions 
    WHERE image_url IS NULL OR image_url = '' 
    ORDER BY id
""")
rows = cur.fetchall()

print(f"Total questions without images: {len(rows)}")

needs_image_cues = [
    r'ushbu yo\'l belgisi', r'mazkur yo\'l belgisi', r'bu yo\'l belgisi', r'ushbu belgi',
    r'mazkur belgi', r'qaysi belgi', r'quyidagi belgilar', r'ushbu chiziq', r'mazkur chiziq',
    r'rasmda', r'suratda', r'ushbu vaziyatda', r'ko\'rsatilgan vaziyatda', r'qizil avtomobil',
    r'sariq avtomobil', r'ko\'k avtomobil', r'yashil avtomobil', r'chorrahadan birinchi bo\'lib o\'tadi'
]
needs_img_regex = re.compile('|'.join(needs_image_cues), re.IGNORECASE)

missing_visual_candidates = []
for r in rows:
    qid, cat, text, oa, ob, oc, od, corr, exp = r
    if needs_img_regex.search(text):
        missing_visual_candidates.append({
            "id": qid,
            "category": cat,
            "text": text,
            "explanation": exp
        })

print(f"Questions without images that mention visual cues: {len(missing_visual_candidates)}")
for q in missing_visual_candidates[:20]:
    print(f"ID {q['id']:3d} ({q['category']:8s}): {q['text']}")
    print(f"   EXP: {str(q['explanation'])[:80]}...\n")

con.close()
