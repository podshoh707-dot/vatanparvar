import json

with open("scratch/questions_no_keywords.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total: {len(items)}\n")

for i, q in enumerate(items[:30]):
    print(f"[{i+1}] ID {q['id']} ({q['category']}):")
    print(f"    Text: {q['text']}")
    print(f"    IMG: {q['image_url']}")
    print(f"    Opts: A: {q['option_a'][:40]} | B: {q['option_b'][:40]}")
    print()
