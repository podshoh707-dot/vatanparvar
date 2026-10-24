import json
import re

with open("scratch/questions_no_keywords.json", "r", encoding="utf-8") as f:
    items = json.load(f)

# Criteria for pure theory:
# If the question can be completely understood and answered purely from the text of the question and options,
# without needing to see any diagram, sign, or picture.
# Especially when options are textual rule statements like:
# "Tartibga solingan chorrahalarda", "Ruxsat etiladi", "Taqiqlanadi", "100 km/s", etc.

pure_theory_list = []
situation_list = []

for q in items:
    text = q["text"].strip()
    t_low = text.lower()
    oa = (q["option_a"] or "").lower()
    ob = (q["option_b"] or "").lower()
    img = q["image_url"]

    # Does text refer to specific vehicle colors or specific visual objects?
    has_vehicle_color = any(c in t_low for c in ['qizil', 'sariq', 'yashil', 'ko\'k', 'oq', 'qora'])
    has_relative_situation = any(w in t_low for w in ['sizning avtomobilingiz', 'siz yaqinlashib', 'oldinda to\'xtab turgan'])
    
    # Check if options refer to colors
    opt_has_color = any(c in oa or c in ob for c in ['qizil', 'sariq', 'yashil', 'ko\'k', 'oq', 'qora'])

    if has_vehicle_color or opt_has_color:
        situation_list.append(q)
    elif any(w in t_low for w in ['ushbu', 'mazkur', 'shu joyda', 'holatda']) and not any(w in t_low for w in ['qanday hollarda', 'qaysi hollarda']):
        situation_list.append(q)
    else:
        pure_theory_list.append(q)

print(f"Total questions without keywords: {len(items)}")
print(f"Classified as Pure Theory (MUST NOT HAVE IMAGE): {len(pure_theory_list)}")
print(f"Classified as Situation/Diagram (NEEDS VERIFICATION): {len(situation_list)}")

with open("scratch/classified_pure_theory.json", "w", encoding="utf-8") as f:
    json.dump(pure_theory_list, f, ensure_ascii=False, indent=2)

with open("scratch/classified_situations.json", "w", encoding="utf-8") as f:
    json.dump(situation_list, f, ensure_ascii=False, indent=2)

print("\n--- SAMPLE PURE THEORY (should have image_url = None) ---")
for q in pure_theory_list[:15]:
    print(f"ID {q['id']} ({q['category']}): {q['text']}")
    print(f"   CURRENT WRONG IMG: {q['image_url']}\n")

print("\n--- SAMPLE SITUATIONS (need image verification) ---")
for q in situation_list[:15]:
    print(f"ID {q['id']} ({q['category']}): {q['text']}")
    print(f"   IMG: {q['image_url']}\n")
