import os

files = os.listdir("webapp/images")
e_files = [f for f in files if f.startswith("e-avtomaktab")]
print(f"Total e-avtomaktab files: {len(e_files)}")
print("Sample files:", sorted(e_files, key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))[:20])

# Check specific files
for qid in [1, 2, 4, 72, 87, 100, 324, 407, 586]:
    f = f"e-avtomaktab{qid}.jpg"
    p = os.path.join("webapp/images", f)
    if os.path.exists(p):
        print(f"Found {f}: size = {os.path.getsize(p)} bytes")
    else:
        print(f"NOT found: {f}")
