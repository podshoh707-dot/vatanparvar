import json
import sqlite3
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/audit_results_clear.json", "r", encoding="utf-8") as f:
    cleared_ids = set(q["id"] for q in json.load(f))

with open("scratch/all_805_questions.json", "r", encoding="utf-8") as f:
    all_qs = json.load(f)

visual_phrases = [
    r'ushbu yo\'l belgisi', r'mazkur yo\'l belgisi', r'bu yo\'l belgisi', r'ushbu belgi',
    r'mazkur belgi', r'bu belgi', r'qaysi belgi', r'quyidagi belgilar', r'bunday belgi',
    r'ushbu chiziq', r'mazkur chiziq', r'bu chiziq', r'ushbu tik chiziq', r'bu tik yo\'l chizig\'i',
    r'ushbu svetofor', r'mazkur svetofor', r'chorrahadan birinchi', r'chorrahani birinchi',
    r'chorrahadan ikkinchi', r'chorrahadan oxirgi', r'tartibda o\'tadilar', r'tartibda o‘tadilar',
    r'suratdagi', r'rasmdagi', r'ushbu vaziyatda', r'mazkur vaziyatda', r'ko\'rsatilgan vaziyatda',
    r'koʻrsatilgan vaziyatda', r'ushbu holatda', r'mazkur holatda', r'ko\'rsatilgan holatda',
    r'koʻrsatilgan holatda', r'yo\'naltirgichlarning qaysilari', r'qaysi yo\'nalishda harakatlanishga ruxsat',
    r'qaysi yo\'nalishlarda harakatlanishga ruxsat', r'qaysi transport vositasiga harakatlanish ruxsat',
    r'harakatlanish kimga ruxsat etilgan\?', r'harakatlanish taqiqlanadi:',
    r'qizil avtomobil', r'sariq avtomobil', r'yashil avtomobil', r'ko\'k avtomobil', r'oq avtomobil'
]
visual_regex = re.compile('|'.join(visual_phrases), re.IGNORECASE)

remaining = [q for q in all_qs if q["image_url"] and q["id"] not in cleared_ids]
not_clearly_visual = [q for q in remaining if not visual_regex.search(q["text"])]

with open("scratch/not_clearly_visual.json", "w", encoding="utf-8") as f:
    json.dump(not_clearly_visual, f, ensure_ascii=False, indent=2)

print(f"Total remaining with images: {len(remaining)}")
print(f"Saved {len(not_clearly_visual)} items to scratch/not_clearly_visual.json")
