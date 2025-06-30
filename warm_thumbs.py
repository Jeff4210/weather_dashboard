#!/usr/bin/env python3
import os
import glob
from tqdm import tqdm
from app import app, OUTPUT_BASE, THUMB_BASE, make_thumb

def collect_sources():
    """Yield every image file under OUTPUT_BASE."""
    exts = ('.jpg', '.jpeg', '.png')
    for root, _, files in os.walk(OUTPUT_BASE):
        for fname in files:
            if fname.lower().endswith(exts):
                yield os.path.join(root, fname)

def regen_thumbs():
    # Gather all images first so tqdm knows the total length
    sources = list(collect_sources())

    # Ensure the thumb base exists
    os.makedirs(THUMB_BASE, exist_ok=True)

    # Iterate with a progress bar
    for src in tqdm(sources, desc="Generating thumbnails", unit="img"):
        # compute the target path under THUMB_BASE
        rel = os.path.relpath(src, OUTPUT_BASE)
        dst = os.path.join(THUMB_BASE, rel)

        # skip if thumbnail already exists and is newer than the source
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue

        # otherwise generate it
        try:
            make_thumb(src)
        except Exception as e:
            # fallback: print error and keep going
            print(f"❌ Failed {src!r}: {e}")

if __name__ == "__main__":
    # enter Flask context so make_thumb (and url_for/current_app) will work
    with app.app_context():
        regen_thumbs()
