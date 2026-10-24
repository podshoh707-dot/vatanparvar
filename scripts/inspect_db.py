import sqlite3
import json

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("SELECT id, category, text, image_url, correct_option, explanation FROM questions WHERE id = 72")
print("Row 72:", cur.fetchone())

cur.execute("SELECT id, category, text, image_url FROM questions WHERE image_url LIKE '%9.7.jpg%'")
print("Questions with 9.7.jpg:", cur.fetchall())

# Let's see all distinct image_urls or patterns in database
cur.execute("SELECT id, category, text, image_url FROM questions WHERE image_url IS NOT NULL LIMIT 20")
for r in cur.fetchall():
    print(r)

con.close()
