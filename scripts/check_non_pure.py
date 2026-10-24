import json

with open("scratch/audit_mismatched_images.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total: {len(items)}")

# Print items that were NOT marked as pure text
non_pure = [x for x in items if not x["is_pure_text"]]
print(f"Non-pure count: {len(non_pure)}")

# Let's see some non-pure questions and their images
print("\n--- NON-PURE SAMPLES ---")
for x in non_pure[:30]:
    print(f"ID {x['id']} ({x['category']}): {x['text'][:65]} -> {x['image_url']}")
