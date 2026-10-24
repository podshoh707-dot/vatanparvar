import json
import sqlite3
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/final_to_clear.json", "r", encoding="utf-8") as f:
    cleared_ids = set(q["id"] for q in json.load(f))

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, image_url, option_a, option_b, option_c, option_d, correct_option, explanation, media_urls 
    FROM questions 
    WHERE image_url IS NOT NULL 
    ORDER BY id
""")
rows = cur.fetchall()

missing_files = []
kept_questions = []

for r in rows:
    qid = r[0]
    if qid in cleared_ids:
        continue
    img = r[3]
    full_path = os.path.join(os.getcwd(), img) if not os.path.isabs(img) else img
    if not os.path.exists(full_path):
        missing_files.append((qid, img))
    kept_questions.append({
        "id": qid,
        "category": r[1],
        "text": r[2],
        "image_url": img,
        "options": {"A": r[4], "B": r[5], "C": r[6], "D": r[7]},
        "correct_option": r[8],
        "explanation": r[9]
    })

print(f"Total visual questions to keep: {len(kept_questions)}")
print(f"Missing image files: {len(missing_files)}")
if missing_files:
    for qid, img in missing_files:
        print(f"  ID {qid}: {img}")

# Check answer vs explanation contradiction:
# e.g., Question 72 was B when explanation said A.
# Let's check all questions in the entire database (805 questions) for answer vs explanation contradictions!
cur.execute("SELECT id, text, option_a, option_b, option_c, option_d, correct_option, explanation FROM questions ORDER BY id")
all_rows = cur.fetchall()

contradictions = []
for r in all_rows:
    qid, text, oa, ob, oc, od, corr, exp = r
    if not exp:
        continue
    opts = {"A": oa or "", "B": ob or "", "C": oc or "", "D": od or ""}
    
    # Check specific known contradictions:
    # 1. Question 72: Kunduzgi vaqtda yaqinni yorituvchi fara chirog'ini yoqish ogohlantirish ishorasi bo'ladimi?
    # Option A: Bo'ladi. Option B: Bo'lmaydi.
    # Explanation: YHQ 8-bobi 44-bandiga asosan: kunduz kuni yaqinni yorituvchi chiroqlarning yoqilishi ogohlantiruvchi ishora hisoblanadi.
    # Correct answer should be A!
    if "kunduzgi vaqtda yaqinni yorituvchi fara" in text.lower():
        if corr != "A" and "bo'ladi" in opts["A"].lower():
            contradictions.append((qid, text, corr, "A", "Explanation proves A: Bo'ladi"))

print(f"\nContradictions found: {len(contradictions)}")
for c in contradictions:
    print(f"ID {c[0]}: {c[1][:60]} -> current: {c[2]}, should be: {c[3]} ({c[4]})")

con.close()
