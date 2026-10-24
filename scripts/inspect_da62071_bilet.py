import subprocess
import json

git_exe = r"C:\Users\user\AppData\Local\GitHubDesktop\app-3.6.7\resources\app\git\cmd\git.exe"
out = subprocess.check_output([git_exe, 'show', 'da62071:database/questions_data.json'], encoding='utf-8')
data = json.loads(out)

print(f"Total questions in da62071: {len(data)}")

for bilet in ["9-Bilet", "10-Bilet", "21-Bilet"]:
    print(f"\n=== {bilet} IN da62071 ===")
    bqs = [q for q in data if q.get('category') == bilet]
    for q in bqs:
        print(f"ID {q['id']}: {q['text'][:70]} -> IMG: {q['image_url']}")
