import sqlite3
import os

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("SELECT id, category, text, image_url, explanation FROM questions ORDER BY id")
rows = cur.fetchall()

print(f"Total questions: {len(rows)}")

# Let's check how many have image_url
with_img = [r for r in rows if r[3]]
no_img = [r for r in rows if not r[3]]

print(f"With image: {len(with_img)}")
print(f"No image: {len(no_img)}")

# Check questions where image exists
# We want to see cases where the question text does NOT mention anything visual (belgi, chiziq, rasm, chorraha, transport, svetofor, etc.)
# but has an image!
suspicious_pure_text_with_img = []
signs_and_intersections_with_img = []

visual_keywords = [
    'belgi', 'chiziq', 'surat', 'rasm', 'chorraha', 'avtomobil', 'transport', 
    'svetofor', 'tartibga soluvchi', 'qaysi biri', 'tartibda', 'ko\'rsatilgan', 
    'koʻrsatilgan', 'ushbu', 'mazkur', 'yo\'nalish', 'yoʻnalish', 'ustunlik',
    'harakatlanish tartibi', 'yo\'l bering', 'yoʻl bering', 'quvib o\'tish',
    'to\'xtash', 'toʻxtash', 'to\'xtab turish', 'toʻxtab turish', 'o\'tadi', 'oʻtadi'
]

for r in with_img:
    qid, cat, text, img, exp = r
    t_lower = text.lower()
    
    # check if any visual keyword is present
    has_visual = any(k in t_lower for k in visual_keywords)
    if not has_visual:
        suspicious_pure_text_with_img.append((qid, cat, text, img))
    else:
        signs_and_intersections_with_img.append((qid, cat, text, img))

print(f"\nSuspicious questions with images (no common visual keyword): {len(suspicious_pure_text_with_img)}")
for qid, cat, text, img in suspicious_pure_text_with_img[:20]:
    print(f"QID {qid} ({cat}): {text}")
    print(f"   -> IMG: {img}\n")

con.close()
