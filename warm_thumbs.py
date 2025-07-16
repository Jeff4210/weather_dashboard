#!/usr/bin/env python3
import os

# Use tqdm if available, otherwise fallback to identity
try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

from app import app, OUTPUT_BASE, THUMB_BASE, LARGE_THUMB_BASE, make_thumb

# Thumbnail specs
SMALL_SIZE    = (300, 300)
SMALL_QUALITY = 75
LARGE_SIZE    = (800, 800)
LARGE_QUALITY = 90

# Only process GOES M1/M2 imagery
VALID_CHANNEL_MARKERS = ("_M1_", "_M2_")

def collect_sources():
    """
    Yield valid GOES image files under OUTPUT_BASE,
    skipping thumbnail dirs and CUSTOMLUT/QC subfolders.
    """
    exts = ('.jpg', '.jpeg', '.png')
    for root, _, files in os.walk(OUTPUT_BASE, followlinks=True):
        if root.startswith(THUMB_BASE) or root.startswith(LARGE_THUMB_BASE):
            continue
        if "CUSTOMLUT" in root or "QC" in root:
            continue

        for fname in files:
            if not fname.lower().endswith(exts):
                continue
            if not any(marker in fname for marker in VALID_CHANNEL_MARKERS):
                continue
            yield os.path.join(root, fname)

def regen_thumbs():
    """Generate thumbnails for all valid GOES images."""
    sources = list(collect_sources())
    os.makedirs(THUMB_BASE, exist_ok=True)
    os.makedirs(LARGE_THUMB_BASE, exist_ok=True)

    for src in tqdm(sources):
        try:
            make_thumb(src, THUMB_BASE, SMALL_SIZE, SMALL_QUALITY)
            make_thumb(src, LARGE_THUMB_BASE, LARGE_SIZE, LARGE_QUALITY)
        except Exception as e:
            print(f"❌ Failed on {src}: {e}")

if __name__ == "__main__":
    with app.app_context():
        regen_thumbs()
