import sqlite3
import json
import os

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation, media_urls
    FROM questions
    ORDER BY id
""")
rows = cur.fetchall()

report = []
for r in rows:
    qid, cat, text, img, oa, ob, oc, od, corr, exp, murls = r
    report.append({
        "id": qid,
        "category": cat,
        "text": text,
        "image_url": img,
        "options": {"A": oa, "B": ob, "C": oc, "D": od},
        "correct_option": corr,
        "explanation": exp,
        "media_urls": murls
    })

with open("scratch/all_805_questions.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Exported {len(report)} questions to scratch/all_805_questions.json")
con.close()
