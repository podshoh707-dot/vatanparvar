import json
import sqlite3

# Check da62071 ID 72 and ID 87
import subprocess
git_exe = r"C:\Users\user\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd\git.exe"
out = subprocess.check_output([git_exe, 'show', 'da62071:database/questions_data.json'], encoding='utf-8')
data = json.loads(out)

q_by_id = {q['id']: q for q in data}

print("da62071 ID 72:", q_by_id.get(72, {}).get('text'), "-> IMG:", q_by_id.get(72, {}).get('image_url'))
print("da62071 ID 87:", q_by_id.get(87, {}).get('text'), "-> IMG:", q_by_id.get(87, {}).get('image_url'))

# Now check current database ID 72
con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()
cur.execute("SELECT id, category, text, image_url, correct_option FROM questions WHERE id IN (71, 72, 73, 87)")
for r in cur.fetchall():
    print("Current DB ID", r[0], f"({r[1]}):", r[2][:60], "-> IMG:", r[3], "CORR:", r[4])
con.close()
