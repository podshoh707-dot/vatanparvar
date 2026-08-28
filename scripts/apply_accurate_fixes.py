import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
QDATA_PATH = os.path.join(BASE_DIR, "database", "questions_data.json")
WEBAPP_PATH = os.path.join(BASE_DIR, "webapp", "questions.json")
DB_JSON_PATH = os.path.join(BASE_DIR, "db", "questions.json")

# Verified corrections
CORRECTIONS = {
    717: "D",
    791: "C",
    811: "C",
    825: "C",
    853: "C",
    860: "C",
    915: "D"
}

# 1. Update database/questions_data.json
with open(QDATA_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)

for q in questions:
    qid = q.get("id")
    if qid in CORRECTIONS:
        old = q.get("correct_option")
        q["correct_option"] = CORRECTIONS[qid]
        print(f"Updated questions_data.json ID {qid}: {old} -> {CORRECTIONS[qid]}")

with open(QDATA_PATH, "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

# 2. Update db/database.sqlite
con = sqlite3.connect(DB_PATH)
cur = con.cursor()
for qid, new_corr in CORRECTIONS.items():
    cur.execute("UPDATE questions SET correct_option = ? WHERE id = ?", (new_corr, qid))
con.commit()
con.close()
print("Updated SQLite database questions table.")

# 3. Update webapp/questions.json
webapp_questions = []
for q in questions:
    opts = []
    if q.get('option_a'): opts.append({'letter': 'A', 'text': q['option_a']})
    if q.get('option_b'): opts.append({'letter': 'B', 'text': q['option_b']})
    if q.get('option_c'): opts.append({'letter': 'C', 'text': q['option_c']})
    if q.get('option_d'): opts.append({'letter': 'D', 'text': q['option_d']})
    
    item = {
        'id': q.get('id'),
        'text': q.get('text'),
        'image_url': q.get('image_url'),
        'media_type': q.get('media_type', 'image'),
        'media_urls': q.get('media_urls'),
        'option_a': q.get('option_a'),
        'option_b': q.get('option_b'),
        'option_c': q.get('option_c'),
        'option_d': q.get('option_d'),
        'options': opts,
        'correct_option': q.get('correct_option', 'A'),
        'correct': q.get('correct_option', 'A'),
        'explanation': q.get('explanation'),
        'difficulty': q.get('difficulty', 'o\'rta'),
        'category': q.get('category', 'Umumiy')
    }
    webapp_questions.append(item)

with open(WEBAPP_PATH, 'w', encoding='utf-8') as f:
    json.dump(webapp_questions, f, ensure_ascii=False, indent=2)

with open(DB_JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print("All database and JSON files successfully updated and synced!")
