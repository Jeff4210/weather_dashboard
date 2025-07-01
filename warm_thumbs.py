#!/usr/bin/env python3
import os
import glob
from tqdm import tqdm

from app import app, OUTPUT_BASE, THUMB_BASE, LARGE_THUMB_BASE, make_thumb

# thumbnail specs
SMALL_SIZE    = (300, 300)
SMALL_QUALITY = 75
LARGE_SIZE    = (800, 800)
LARGE_QUALITY = 90

def collect_sources():
    """Yield every image file under OUTPUT_BASE."""
    exts = ('.jpg', '.jpeg', '.png')
    for root, _, files in os.walk(OUTPUT_BASE):
        for fname in files:
            if fname.lower().endswith(exts):
                yield os.path.join(root, fname)

def regen_thumbs():
    # gather all sources so tqdm can show total
    sources = list(collect_sources())

    # ensure both thumb directories exist
    os.makedirs(THUMB_BASE, exist_ok=True)
    os.makedirs(LARGE_THUMB_BASE, exist_ok=True)

    for src in tqdm(sources, desc="Generating thumbnails", unit="img"):
        # relative path under OUTPUT_BASE
        rel = os.path.relpath(src, OUTPUT_BASE)

        # small thumb
        dst_small = os.path.join(THUMB_BASE, rel)
        if not os.path.exists(dst_small) or os.path.getmtime(dst_small) < os.path.getmtime(src):
            try:
                make_thumb(src, THUMB_BASE, SMALL_SIZE, SMALL_QUALITY)
            except Exception as e:
                print(f"❌ Small-thumb failed for {src!r}: {e}")

        # large thumb
        dst_large = os.path.join(LARGE_THUMB_BASE, rel)
        if not os.path.exists(dst_large) or os.path.getmtime(dst_large) < os.path.getmtime(src):
            try:
                make_thumb(src, LARGE_THUMB_BASE, LARGE_SIZE, LARGE_QUALITY)
            except Exception as e:
                print(f"❌ Large-thumb failed for {src!r}: {e}")

if __name__ == "__main__":
    # need Flask context for make_thumb's logger
    with app.app_context():
        regen_thumbs()
