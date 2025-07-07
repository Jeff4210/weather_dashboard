#!/usr/bin/env python3
import os
from PIL import Image

# ─── CONFIG ────────────────────────────────────────────────────────────────
# Root of your STPI output images
OUTPUT_BASE       = os.path.join(os.path.dirname(__file__),
                                 "static", "output", "stpi")
# Where to put the small and large thumbs
SMALL_THUMB_BASE  = os.path.join(os.path.dirname(__file__),
                                 "static", "thumbs", "stpi")
LARGE_THUMB_BASE  = os.path.join(os.path.dirname(__file__),
                                 "static", "thumbs_large", "stpi")

# Thumbnail sizes & quality
SMALL_SIZE   = (300, 300)
SMALL_QUALITY= 85
LARGE_SIZE   = (800, 800)
LARGE_QUALITY= 95

def make_thumb(src_path: str, dst_base: str, size: tuple[int,int], quality: int):
    """
    Mirror src_path under dst_base, resizing to `size` and saving as JPEG at `quality`.
    Only regenerates if src is newer than dst or dst is missing.
    """
    rel = os.path.relpath(src_path, OUTPUT_BASE)
    dst  = os.path.join(dst_base, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if not os.path.exists(dst) or os.path.getmtime(src_path) > os.path.getmtime(dst):
        print(f"Generating thumbnail: {dst}")
        with Image.open(src_path) as im:
            # ← NEW: convert any mode to RGB so thumbnail() works
            im = im.convert("RGB")
            im.thumbnail(size)
            im.save(dst, "JPEG", quality=quality)

    return dst

def main():
    # Walk every image under static/output/stpi/
    for root, dirs, files in os.walk(OUTPUT_BASE):
        for fn in files:
            if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            src = os.path.join(root, fn)
            # small thumb
            make_thumb(src, SMALL_THUMB_BASE, SMALL_SIZE, SMALL_QUALITY)
            # large thumb
            make_thumb(src, LARGE_THUMB_BASE, LARGE_SIZE, LARGE_QUALITY)

if __name__ == "__main__":
    main()
