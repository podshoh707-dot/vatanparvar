import sqlite3
import re
import json

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("PRAGMA table_info(questions)")
columns = [c[1] for c in cur.fetchall()]
print("Columns in questions table:", columns)

cur.execute(f"SELECT {', '.join(columns)} FROM questions ORDER BY id")
rows = cur.fetchall()
col_map = {name: idx for idx, name in enumerate(columns)}
print(f"Total questions in DB: {len(rows)}")

with_images = [r for r in rows if r[col_map['image_url']] and str(r[col_map['image_url']]).strip()]
print(f"Questions with image_url: {len(with_images)}")

# Sample questions with image_url
print("\n--- SAMPLE WITH IMAGES ---")
for r in with_images[:15]:
    qid = r[col_map['id']]
    cat = r[col_map['category']]
    txt = r[col_map['text']]
    img = r[col_map['image_url']]
    print(f"ID {qid} ({cat}): {txt[:70]}... -> IMG: {img}")

# Let's check distribution of image paths
img_types = {}
for r in with_images:
    img = str(r[col_map['image_url']])
    prefix = img.split('/')[0] if '/' in img else 'root'
    img_types[prefix] = img_types.get(prefix, 0) + 1
print(f"\nImage path prefixes: {img_types}")

con.close()
