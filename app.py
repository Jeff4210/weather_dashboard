#!/usr/bin/env python3
import os
import re          
import json
import glob
import threading
import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
from flask import (
    Flask, render_template, send_from_directory, abort,
    url_for, request, current_app, jsonify
)
from PIL import Image
# ─── Configuration ────────────────────────────────────────────────────────────
OUTPUT_BASE = os.getenv(
    "GOES_OUTPUT_BASE",
    os.path.join(os.path.dirname(__file__), "static", "output", "goes19")
)
THUMB_BASE       = os.path.join(os.path.dirname(__file__), "static", "thumbs")
LARGE_THUMB_BASE = os.path.join(os.path.dirname(__file__), "static", "thumbs_large")

REGION_TITLES = {
    "fd": "Full-Disk (FD)",
    "m1": "Meso-1 (M1)",
    "m2": "Meso-2 (M2)",
}
CHANNEL_NAMES = {
    "ch01": "Blue (0.47 μm)",    "ch02": "Red (0.64 μm)",
    "ch03": "Vegetation (0.86 μm)","ch04": "Cirrus (1.37 μm)",
    "ch05": "Snow/Ice (1.6 μm)",   "ch06": "Cloud Particle Size (2.2 μm)",
    "ch07": "Shortwave IR (3.9 μm)","ch08": "Upper-Level WV (6.2 μm)",
    "ch09": "Mid-Level WV (6.95 μm)","ch10": "Low-Level WV (7.34 μm)",
    "ch11": "Cloud-Top Phase (8.4 μm)","ch12": "Ozone (9.6 μm)",
    "ch13": "Clean IR (10.3 μm)",   "ch14": "Split-Window IR (11.2 μm)",
    "ch15": "Ash (12.3 μm)",        "ch16": "Upper-Level WV (13.3 μm)",
    "FC":   "False Color Composite", "CUSTOMLUT":"Custom LUT"
}

# ─── In-memory manifest + lock ────────────────────────────────────────────────
_manifest      = {}
_manifest_lock = threading.Lock()
# ─── Manifest builder ─────────────────────────────────────────────────────────
def build_manifest():
    """
    Walk every JPEG under OUTPUT_BASE/<region>/<channel>/<date>/filename.jpg
    and bucket them by region→channel→timestamp→variant.
    """
    new_manifest = {}

    for region in REGION_TITLES:
        region_root = os.path.join(OUTPUT_BASE, region)
        if not os.path.isdir(region_root):
            continue

        region_dict = {}
        # Glob for all JPGs three levels deep: region/channel/date/file.jpg
        pattern = os.path.join(region_root, "*", "*", "*.jpg")
        for path in glob.glob(pattern):
            # Extract channel, date and filename from the path
            # e.g. /.../output/goes19/fd/ch02/2025-07-05/FN.jpg
            parts = path.split(os.sep)
            channel = parts[-3]
            date    = parts[-2]
            fn      = parts[-1]

            if channel not in CHANNEL_NAMES:
                continue

            fn_lc = fn.lower()
            ts = variant = None

            # 1) CUSTOMLUT composite
            if channel.upper() == "CUSTOMLUT":
                m = re.match(
                    r".*_(\d{8}t\d{6}z)_fc_customlut_(clean|map|enhanced_clean|enhanced_map)\.jpg$",
                    fn_lc
                )
                if m:
                    ts, variant = m.groups()

            # 2) FC composite
            elif channel.upper() == "FC":
                m = re.match(
                    r".*_(\d{8}t\d{6}z)_fc_(clean|map|enhanced_clean|enhanced_map)\.jpg$",
                    fn_lc
                )
                if m:
                    ts, variant = m.groups()

            # 3) Spectral bands (ch01–ch16)
            else:
                # a) enhanced variants: …_enhanced_<TS>_<type>.jpg
                m = re.match(
                    r".*_enhanced_(\d{8}t\d{6}z)_(clean|map)\.jpg$",
                    fn_lc
                )
                if m:
                    ts, v = m.groups()
                    variant = f"enhanced_{v}"
                else:
                    # b) clean/map variants: …_<TS>_<type>.jpg
                    m2 = re.match(
                        r".*_(\d{8}t\d{6}z)_(clean|map)\.jpg$",
                        fn_lc
                    )
                    if m2:
                        ts, variant = m2.groups()

            if not ts or not variant:
                continue

            # build per-channel, per-timestamp bucket
            ch_buckets = region_dict.setdefault(
                channel,
                defaultdict(lambda: {
                    "clean": None,
                    "map": None,
                    "enhanced_clean": None,
                    "enhanced_map": None,
                    "time": None
                })
            )
            bucket = ch_buckets[ts]
            bucket[variant] = f"/thumbnails_large/{region}/{channel}/{date}/{fn}"

            # record human‐readable time (once)
            if bucket["time"] is None:
                dt = datetime.datetime.strptime(ts.upper(), "%Y%m%dT%H%M%SZ")
                dt = dt.replace(tzinfo=datetime.timezone.utc) \
                       .astimezone(ZoneInfo("America/New_York"))
                bucket["time"] = dt.strftime("%Y-%m-%d %I:%M %p")

        # now convert each channel’s buckets into a sorted list
        for ch, tb in region_dict.items():
            # sort timestamps ascending, then keep them all
            entries = [tb[t] for t in sorted(tb)]
            region_dict[ch] = entries

        if region_dict:
            new_manifest[region] = region_dict

    # atomically swap into the global manifest
    with _manifest_lock:
        _manifest.clear()
        _manifest.update(new_manifest)

    return new_manifest
# ─── Get Manifest ─────────────────────────────────────────────────────────────
def get_manifest():
    """Thread-safe snapshot of the in-memory manifest."""
    with _manifest_lock:
        # return a shallow copy so callers can’t mutate our internal dict
        return { region: dict(chs) for region, chs in _manifest.items() }

# ─── 2) CALL it once, now that it’s defined ─────────────────────────
build_manifest()
# ─── Flask app setup ────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# DEBUG: once, at startup
with app.app_context():
    for region in REGION_TITLES:
        region_root = os.path.join(OUTPUT_BASE, region)
        app.logger.debug(f"DEBUG: {region_root} subfolders = {os.listdir(region_root)!r}")
# ─── Health-check endpoint ────────────────────────────────────────────────────
@app.route("/ping")
def ping():
    return "pong", 200
# ─── Context Processor ──────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
      'CHANNEL_NAMES': CHANNEL_NAMES,
      'REGION_TITLES':  REGION_TITLES
    }
# ─── Thumbnail generator ──────────────────────────────────────────────────────
def make_thumb(src_path, dst_base, size, quality):
    """
    Ensure a thumbnail of `src_path` exists under `dst_base` (mirroring dirs),
    resized to `size` (tuple), saved as JPEG at `quality`.
    Returns the filesystem path of the thumbnail.
    """
    rel = os.path.relpath(src_path, OUTPUT_BASE)
    dst = os.path.join(dst_base, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src_path):
        current_app.logger.debug(f"Generating thumb: {src_path} -> {dst}")
        im = Image.open(src_path)
        im.thumbnail(size)
        im.save(dst, "JPEG", quality=quality)

    return dst

# ─── Index view ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    manifest = get_manifest()
    sections = []

    for region_slug, region_title in REGION_TITLES.items():
        CUSTOMLUT_history = manifest.get(region_slug, {}).get("CUSTOMLUT", [])
        if not CUSTOMLUT_history:
            continue

        latest = CUSTOMLUT_history[-1]
        # use the large thumbs route
        relpath   = latest["clean"].split("/thumbnails_large/", 1)[1]
        thumb_url = url_for("serve_large_thumb", filename=relpath)
        link_url  = url_for("region_page", region=region_slug)

        sections.append({
            "link":  link_url,
            "label": region_title,
            "thumb": thumb_url
        })

    return render_template("index.html", sections=sections)
# ─── Serve master images ───────────────────────────────────────────────────────
@app.route("/images/<region>/<channel>/<date>/<filename>")
def serve_image(region, channel, date, filename):
    folder = os.path.join(OUTPUT_BASE, region, channel, date)
    if not os.path.isdir(folder):
        abort(404)
    return send_from_directory(folder, filename)


# ─── Serve small thumbs ─────────────────────────────────────────────────────────
@app.route("/thumbnails/<path:filename>")
def serve_thumb(filename):
    # find the original in OUTPUT_BASE
    src = os.path.join(OUTPUT_BASE, filename)
    if not os.path.isfile(src):
        abort(404)

    # generate (or re-generate) the small thumb under THUMB_BASE
    thumb_path = make_thumb(src, THUMB_BASE, size=(300,300), quality=85)

    folder, fname = os.path.split(thumb_path)
    return send_from_directory(folder, fname, mimetype="image/jpeg")

# ─── Serve large thumbs ─────────────────────────────────────────────────────────
@app.route("/thumbnails_large/<path:filename>")
def serve_large_thumb(filename):
# build path to the original full-res image
    # filename is e.g. "fd/ch02/2025-07-05/GOES19_FD_20250705T120021Z_clean.jpg"
    src_orig = os.path.join(OUTPUT_BASE, filename)
    if not os.path.isfile(src_orig):
        abort(404)
    # generate an 800×800-max thumbnail from the original
    thumb_large = make_thumb(src_orig, LARGE_THUMB_BASE, size=(800,800), quality=95)
    folder, fname = os.path.split(thumb_large)
    return send_from_directory(folder, fname, mimetype="image/jpeg")

# ─── Region page (grid + toggles) ────────────────────────────────────────────
@app.route("/<region>")
def region_page(region):
    r = region.lower()
    with _manifest_lock:
        region_data = _manifest.get(r, {})
    if not region_data:
        abort(404)

    files_info = []
    # iterate in CHANNEL_NAMES order, but only include ones with data
    for ch in CHANNEL_NAMES:
        history = region_data.get(ch)
        if not history:
            continue

        # pick the newest timestamp; our build_manifest sorted ascending
        frame = history[-1]

        # wrap into the structure your template expects:
        files_info.append({
            "slug":    ch,
            "display": CHANNEL_NAMES[ch],
            "clean":   {"thumb": frame["clean"],            "time": frame["time"]},
            "map":     ({"thumb": frame["map"],              "time": frame["time"]}   if frame.get("map")         else None),
            "enh_clean":({"thumb": frame.get("enhanced_clean"), "time": frame["time"]}   if frame.get("enhanced_clean") else None),
            "enh_map":  ({"thumb": frame.get("enhanced_map"),   "time": frame["time"]}   if frame.get("enhanced_map")   else None),
        })

    return render_template(
        "region.html",
        region_slug=r,
        region_name=REGION_TITLES.get(r, r),
        files_info=files_info
    )
# ─── Explore page (scrubber timeline) ────────────────────────────────────────
@app.route("/<region>/explore/<channel>")
def explore(region, channel):
    current_app.logger.debug(f"🔎 explore(region={region!r}, channel={channel!r})")

    # pull the pre-built list of frames for this channel
    with _manifest_lock:
        history = _manifest.get(region, {}).get(channel)

    if not history:
        abort(404)

    # now just render with the list, which your template/JS expects
    return render_template(
        "explore.html",
        region_slug=  region,
        channel_slug= channel,
        region_name=  REGION_TITLES.get(region, region),
        channel_name= CHANNEL_NAMES.get(channel, channel),
        history=      history
    )
# ─── Error handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return "Not Found", 404

@app.errorhandler(Exception)
def handle_all_exceptions(e):
    import traceback
    tb = traceback.format_exc()
    current_app.logger.error("Exception on %s %s:\n%s",
                             request.method, request.path, tb)
    return f"<pre>{tb}</pre>", 500

@app.route("/healthz")
def healthz():
    return "OK", 200

# ─── Debug manifest endpoint ─────────────────────────────────────────────────
@app.route("/__manifest__")
def show_manifest():
    # force a fresh scan every time you hit this endpoint
    build_manifest()
    with _manifest_lock:
        snap = dict(_manifest)
    return jsonify(snap)

# ─── Background manifest builder ─────────────────────────────────────────────
def _periodic_build():
    """Rebuild inside a test-request context, then reschedule in 5 minutes."""
    with app.test_request_context():
        build_manifest()
    t = threading.Timer(300, _periodic_build)
    t.daemon = True
    t.start()

def start_build_loop():
    """Do one initial build (with a fake request), then schedule periodic rebuilds."""
    with app.test_request_context():
        build_manifest()
    t = threading.Timer(300, _periodic_build)
    t.daemon = True
    t.start()

@app.after_request
def add_no_cache_headers(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
# ─── Kick off the initial build and periodic rebuilds (after routes!) ─────────
start_build_loop()

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now}
# ─── Debug entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
