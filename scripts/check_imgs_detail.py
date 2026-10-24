import os
from PIL import Image

test_files = [
    "zip/videos/6.6.jpg", "zip/videos/7.3.jpg", "zip/videos/7.7.jpg",
    "zip/videos/9.6.jpg", "zip/videos/9.7.jpg", "zip/videos/9.8.jpg",
    "zip/videos/12-7.jpg", "zip/videos/13-1.jpg", "zip/videos/13.2.jpg"
]

for tf in test_files:
    if os.path.exists(tf):
        im = Image.open(tf)
        print(f"{tf}: {im.size}, {im.format}")
    else:
        print(f"{tf}: NOT FOUND")
