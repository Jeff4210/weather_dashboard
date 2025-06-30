#!/usr/bin/env python3
import os, re, shutil
from pathlib import Path

# Base directories
GOES_BASE   = Path("/home/jeff/weather/shared/goes19")
THUMB_BASE  = Path("/home/jeff/weather/shared/goes19_thumbs")

# Regex to extract YYYYMMDD from filenames like …_20250623T070725Z_…
DATE_RE = re.compile(r"_(\d{8})T\d{6}Z_")

def move_into_date_dirs(base_path: Path):
    for region in base_path.iterdir():
        if not region.is_dir(): continue
        for channel in region.iterdir():
            if not channel.is_dir(): continue

            # Process every file in this channel folder
            for f in list(channel.iterdir()):
                if not f.is_file(): continue
                m = DATE_RE.search(f.name)
                if not m:
                    print(f"  skipping (no date found): {f.name}")
                    continue

                ymd = m.group(1)
                date_dir = channel / f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
                date_dir.mkdir(exist_ok=True)
                dest = date_dir / f.name
                print(f"Moving {f.name} → {date_dir.name}/")
                shutil.move(str(f), str(dest))

def main():
    print("Restructuring raw GOES images…")
    move_into_date_dirs(GOES_BASE)
    print("Restructuring thumbnails…")
    move_into_date_dirs(THUMB_BASE)
    print("✅ Restructure complete.")

if __name__ == "__main__":
    main()
