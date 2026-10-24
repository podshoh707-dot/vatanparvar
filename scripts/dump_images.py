import json

with open("scratch/all_805_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

# Questions with images
with_img = [q for q in questions if q["image_url"]]
print(f"Total questions with images: {len(with_img)}")

# Write all questions with images to a file so we can analyze them completely
with open("scratch/questions_with_images.json", "w", encoding="utf-8") as f:
    json.dump(with_img, f, ensure_ascii=False, indent=2)

print("Saved scratch/questions_with_images.json")
