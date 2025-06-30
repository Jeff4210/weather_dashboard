#!/usr/bin/env python3
import os
import glob
import json
import datetime
import logging
import re
from zoneinfo import ZoneInfo
from tqdm import tqdm

# ─── Configuration ───────────────────────────────────────────────────────────
OUTPUT_BASE   = "/home/jeff/weather/output/goes19"
STATIC_DIR    = "static"
MANIFEST_FILE = os.path.join(STATIC_DIR, "manifest.json")

REGION_TITLES = {
    "fd": "Full-Disk (FD)",
    "m1": "Meso-1 (M1)",
    "m2": "Meso-2 (M2)"
}

CHANNEL_NAMES = {
    "ch01": "Blue (0.47 μm)",
    "ch02": "Red (0.64 μm)",
    "ch03": "Vegetation (0.86 μm)",
    "ch04": "Cirrus (1.37 μm)",
    "ch05": "Snow/Ice (1.6 μm)",
    "ch06": "Cloud Particle Size (2.2 μm)",
    "ch07": "Shortwave IR (3.9 μm)",
    "ch08": "Upper-Level WV (6.2 μm)",
    "ch09": "Mid-Level WV (6.95 μm)",
    "ch10": "Low-Level WV (7.34 μm)",
    "ch11": "Cloud-Top Phase (8.4 μm)",
    "ch12": "Ozone (9.6 μm)",
    "ch13": "Clean IR (10.3 μm)",
    "ch14": "Split-Window IR (11.2 μm)",
    "ch15": "Ash (12.3 μm)",
    "ch16": "Upper-Level WV (13.3 μm)",
    "fc":   "False Color Composite"
}
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def newest(lst):
    return max(lst, key=os.path.getmtime) if lst else None

def discover_regions():
    return list(REGION_TITLES.keys())

def gather_images(region, channel):
    """
    Return (clean_dict, map_dict) for the most‐recent date that has a clean image.
    Each dict is {url, thumb, time} or None.
    """
    base = os.path.join(OUTPUT_BASE, region, channel)
    if not os.path.isdir(base):
        return None, None

    # list all YYYY-MM-DD subdirs, newest first
    dates = sorted(
        [d for d in os.listdir(base)
         if re.match(r"^\d{4}-\d{2}-\d{2}$", d)],
        reverse=True
    )

    for d in dates:
        folder = os.path.join(base, d)
        imgs = sorted(glob.glob(os.path.join(folder, "*.*")),
                      key=os.path.getmtime, reverse=True)
        if not imgs:
            continue

        clean_imgs = [p for p in imgs if "_map." not in os.path.basename(p).lower()]
        map_imgs   = [p for p in imgs if "_map."   in os.path.basename(p).lower()]

        clean_p = newest(clean_imgs)
        map_p   = newest(map_imgs)

        def mkdict(path):
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(path),
                tz=ZoneInfo("America/New_York")
            ).strftime("%Y-%m-%d %I:%M %p")
            rel = os.path.relpath(path, OUTPUT_BASE)
            return {"path": rel, "time": mtime}

        return mkdict(clean_p), mkdict(map_p)

    return None, None

#def build_manifest():
    sections = []
    for region in discover_regions():
        clean, mapp = gather_images(region, "fc")
        if not clean:
            continue
        sections.append({
            "region": region,
            "label":  REGION_TITLES[region],
            "clean":  clean,
            "map":    mapp
        })

    os.makedirs(STATIC_DIR, exist_ok=True)
    with open(MANIFEST_FILE, "w") as fp:
        json.dump({
            "generated": datetime.datetime.now(tz=ZoneInfo("America/New_York"))
                                       .isoformat(),
            "sections":  sections
        }, fp, indent=2)

    logger.info(f"Wrote {len(sections)} sections → {MANIFEST_FILE}")

if __name__ == "__main__":
    build_manifest()
