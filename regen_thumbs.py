#!/usr/bin/env python3
import os, glob, datetime
from PIL import Image, UnidentifiedImageError

OUTPUT_BASE = "/home/jeff/weather/shared/goes19"
THUMB_BASE  = "/home/jeff/weather/shared/goes19_thumbs"
SIZE        = (800, 800)   # your thumbnail max‐dimensions
MIN_BYTES   = 10_000       # skip any files <10 KB (corrupt/incomplete)

for region in os.listdir(OUTPUT_BASE):
    regdir = os.path.join(OUTPUT_BASE, region)
    if not os.path.isdir(regdir): continue

    for ch in os.listdir(regdir):
        chdir = os.path.join(regdir, ch)
        if not os.path.isdir(chdir): continue

        for date in os.listdir(chdir):
            ddir = os.path.join(chdir, date)
            if not os.path.isdir(ddir): continue

            for ext in ("png","jpg","jpeg","PNG","JPG","JPEG"):
                for src in glob.glob(os.path.join(ddir, f"*.{ext}")):
                    if os.path.getsize(src) < MIN_BYTES:
                        # too small, probably half‐written
                        continue

                    rel = os.path.relpath(src, OUTPUT_BASE)
                    dst = os.path.join(THUMB_BASE, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)

                    # skip ones we already have
                    if os.path.exists(dst):
                        continue

                    try:
                        with Image.open(src) as im:
                            im.thumbnail(SIZE)
                            im.save(dst, "JPEG", quality=85)
                        print("✔", dst)
                    except UnidentifiedImageError:
                        print("✘ skip invalid image", src)
                    except Exception as e:
                        print("‼ error on", src, "–", e)
