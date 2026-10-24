import sqlite3

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

query = """
SELECT id, category, text, image_url, explanation 
FROM questions 
WHERE text LIKE '%aholi punkti%' 
   OR text LIKE '%5.24%' 
   OR explanation LIKE '%5.24%' 
   OR explanation LIKE '%Yangibozor%'
   OR text LIKE '%Yangibozor%'
"""
cur.execute(query)
rows = cur.fetchall()
print(f"Found questions: {len(rows)}")
for r in rows:
    print(f"ID {r[0]} ({r[1]}): {r[2]} -> IMG: {r[3]}")
    print(f"   EXP: {r[4][:120]}...\n")

con.close()
