import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open("scratch/not_clearly_visual.json", "r", encoding="utf-8") as f:
    items = json.load(f)

flagged_pure = []
genuine_visual = []

for q in items:
    text = q["text"].strip()
    t_low = text.lower()
    
    # Check for visual anchors in question text:
    has_visual_anchor = any(w in t_low for w in [
        'shu joyda', 'shunday yo\'l belgisi', 'shunday belgi', 'ko\'rsatilgan',
        'ushbu holat', 'mazkur holat', 'ushbu vaziyat', 'mazkur vaziyat',
        'bunday vaziyat', 'bunday holat', 'trayektoriya', 'qizil avtomobil',
        'ko\'k avtomobil', 'yashil avtomobil', 'sariq avtomobil', 'oq avtomobil',
        'qora avtomobil', 'avtomobillardan qaysi biri', 'qaysi transport vositalari yo\'lovchilarni',
        'qaysi transport vositalari to\'xtagan', 'qaysi transport vositasining haydovchisi yo\'l berishi',
        'qaysi transport vositasi haydovchisi yo\'l berishi', 'qaysi transport vositasining haydovchisi birinchi',
        'qaysi transport vositasi haydovchisi to\'g\'riga', 'tartibda o\'tadi', 'birinchi bo\'lib o\'tadi',
        'ikkinchi bo\'lib o\'tadi', 'oxirgi bo\'lib o\'tadi', 'navbatchining haydovchiga qaratilgan qaysi holati',
        'bunday avtopoezdning ko\'prikdan o\'tishiga', 'bu joyda qayrilishga ruxsat',
        'bu joyda quvib o\'tishga ruxsat', 'bu yotiq chiziq', 'ushbu yotiq chiziq',
        'mazkur yotiq chiziq', 'qatnov qismidagi bunday yo\'naltirgichlar',
        'bunday taniqli belgisi', 'bu belgilar aholi yashaydigan', 'bu belgilar qaysi',
        'bu belgida ko\'k fon', 'bu belgilarning qaysi biri', 'mazkur belgilar',
        'shunday belgi bo\'lgan'
    ])
    
    if not has_visual_anchor:
        flagged_pure.append(q)
    else:
        genuine_visual.append(q)

print(f"Total in round 2: {len(items)}")
print(f"Flagged as likely PURE THEORY (no visual anchor): {len(flagged_pure)}")
print(f"Genuine visual situations: {len(genuine_visual)}")

with open("scratch/flagged_pure_round2.json", "w", encoding="utf-8") as f:
    json.dump(flagged_pure, f, ensure_ascii=False, indent=2)

print("\n--- SAMPLES OF FLAGGED PURE (ROUND 2) ---")
for q in flagged_pure[:25]:
    print(f"ID {q['id']:3d} ({q['category']:8s}): {q['text']}")
    print(f"   IMG: {q['image_url']}\n")
