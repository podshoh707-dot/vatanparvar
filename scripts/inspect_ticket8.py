import json

with open('scratch/all_805_questions.json', 'r', encoding='utf-8') as f:
    qs = json.load(f)

for bilet_no in range(7, 10):
    bilet_qs = [q for q in qs if q['category'] == f"{bilet_no}-Bilet"]
    print(f"\n=== {bilet_no}-BILET ===")
    for q in bilet_qs:
        print(f"ID {q['id']}: {q['text']}")
        print(f"   IMG: {q['image_url']}")
        print(f"   CORR: {q['correct_option']} | OPTS: A: {q['options']['A']} | B: {q['options']['B']}")
        print()
