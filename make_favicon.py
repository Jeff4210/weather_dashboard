#!/usr/bin/env python3
import os
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────
# Path to your square source image (JPEG or PNG) in static/
SRC_PATH = os.path.join("static", "favicon.jpg")  # update if your file is named differently

# Output files in static/
ICO_PATH         = os.path.join("static", "favicon.ico")
APPLE_TOUCH_PATH = os.path.join("static", "apple-touch-icon.png")
ANDROID_192_PATH = os.path.join("static", "android-chrome-192x192.png")
ANDROID_512_PATH = os.path.join("static", "android-chrome-512x512.png")

# ICO sizes to embed
ICO_SIZES = [
    (16, 16),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]

# ─── Script ────────────────────────────────────────────────────────────
def main():
    # 1) Verify source exists
    if not os.path.isfile(SRC_PATH):
        print(f"❌ Source file not found: {SRC_PATH}")
        return

    # 2) Load and convert
    im = Image.open(SRC_PATH).convert("RGBA")

    # 3) Generate favicon.ico
    print(f"Generating {ICO_PATH} …")
    im.save(ICO_PATH, format="ICO", sizes=ICO_SIZES)
    print(f"  ✔ Saved {ICO_PATH}")

    # 4) Generate apple-touch-icon.png @ 180×180
    print(f"Generating {APPLE_TOUCH_PATH} at 180×180 …")
    im.resize((180, 180), Image.LANCZOS).save(APPLE_TOUCH_PATH, format="PNG")
    print(f"  ✔ Saved {APPLE_TOUCH_PATH}")

    # 5) Generate Android Chrome icons
    print(f"Generating {ANDROID_192_PATH} at 192×192 …")
    im.resize((192, 192), Image.LANCZOS).save(ANDROID_192_PATH, format="PNG")
    print(f"  ✔ Saved {ANDROID_192_PATH}")

    print(f"Generating {ANDROID_512_PATH} at 512×512 …")
    im.resize((512, 512), Image.LANCZOS).save(ANDROID_512_PATH, format="PNG")
    print(f"  ✔ Saved {ANDROID_512_PATH}")

if __name__ == "__main__":
    main()
