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
BASE_DIR         = os.path.abspath(os.path.dirname(__file__))
OUTPUT_BASE      = os.path.join(BASE_DIR, "static", "output", "goes19")
THUMB_BASE       = os.path.join(BASE_DIR, "static", "thumbs")
LARGE_THUMB_BASE = os.path.join(BASE_DIR, "static", "thumbs_large")

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
    "fc":   "False Color Composite"
}

# ─── In-memory manifest + lock ────────────────────────────────────────────────
_manifest      = {}
_manifest_lock = threading.Lock()
# ─── Manifest builder ─────────────────────────────────────────────────────────
def build_manifest():
    """
    Walk the output directory tree and build a manifest of all
    available thumbnail variants, grouped by timestamp, per region/channel.
    Atomically swaps it into _manifest and returns it.
    """
    new = {}

    for region in REGION_TITLES:
        region_dict = {}

        for channel in CHANNEL_NAMES:
            base_dir = os.path.join(OUTPUT_BASE, region, channel)
            if not os.path.isdir(base_dir):
                continue

            # one bucket per timestamp
            ts_buckets = defaultdict(lambda: {
                "clean": None,
                "map": None,
                "enhanced_clean": None,
                "enhanced_map": None,
                "time": None
            })

            # scan every date folder
            for date in sorted(os.listdir(base_dir)):
                date_dir = os.path.join(base_dir, date)
                if not os.path.isdir(date_dir) or not re.match(r"\d{4}-\d{2}-\d{2}", date):
                    continue

                for fn in os.listdir(date_dir):
                    fn_lc = fn.lower()

                    # pick regex by channel
                    if channel == "fc":
                        # files named like …_20250628T120020Z_fc_clean.jpg
                        pattern = (
                            rf".*_(\d{{8}}t\d{{6}}z)_fc_"
                            r"(clean|map|enhanced_clean|enhanced_map)\.jpg$"
                        )
                    else:
                        # files named like …_ch02_20250628T120020Z_clean.jpg
                        pattern = (
                            rf".*_{channel}_(\d{{8}}t\d{{6}}z)_"
                            r"(clean|map|enhanced_clean|enhanced_map)\.jpg$"
                        )

                    m = re.match(pattern, fn_lc)
                    if not m:
                        continue

                    ts, variant = m.groups()

                    # build the thumbnail URL
                    url_path = f"/thumbnails_large/{region}/{channel}/{date}/{fn}"
                    bucket = ts_buckets[ts]
                    bucket[variant] = url_path

                    # parse & set human time once per timestamp
                    if bucket["time"] is None:
                        # uppercase the Z and parse with strptime
                        ts_uc = ts.upper()  # e.g. "20250628T120020Z"
                        dt = datetime.datetime.strptime(ts_uc, "%Y%m%dT%H%M%SZ")
                        # treat as UTC, convert to local
                        dt = dt.replace(tzinfo=datetime.timezone.utc) \
                               .astimezone(ZoneInfo("America/New_York"))
                        bucket["time"] = dt.strftime("%Y-%m-%d %I:%M %p")

            # convert each bucket into a sorted list
            entries = [ts_buckets[t] for t in sorted(ts_buckets)]
            if entries:
                region_dict[channel] = entries

        if region_dict:
            new[region] = region_dict

    # swap into the global manifest under lock
    with _manifest_lock:
        _manifest.clear()
        _manifest.update(new)

    return new
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
# ─── Health-check endpoint ────────────────────────────────────────────────────
@app.route("/ping")
def ping():
    return "pong", 200

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
        # channels is a dict: channel_slug → [ frame1, frame2, ... ]
        channels = manifest.get(region_slug, {})
        fc_history = channels.get("fc")

        # skip if no FC history
        if not fc_history:
            continue

        # pick the newest frame (last in list)
        latest = fc_history[-1]
        # in the new manifest, latest["clean"] is a URL string
        thumb_url = latest["clean"]

        sections.append({
            "link":  url_for("region_page", region=region_slug),
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


@app.route("/thumbnails/<path:filename>")
def serve_thumb(filename):
    src = os.path.join(OUTPUT_BASE, filename)
    if not os.path.isfile(src):
        abort(404)
    thumb_path = make_thumb(src, THUMB_BASE, size=(300,300), quality=85)
    folder, fname = os.path.split(thumb_path)
    return send_from_directory(folder, fname, mimetype="image/jpeg")

@app.route("/thumbnails_large/<path:filename>")
def serve_large_thumb(filename):
    # build large thumbs *from* the small thumb, so we get consistency
    src = os.path.join(THUMB_BASE, filename)
    if not os.path.isfile(src):
        abort(404)
    thumb_path = make_thumb(src, LARGE_THUMB_BASE, size=(800,800), quality=95)
    folder, fname = os.path.split(thumb_path)
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
    for ch, display in CHANNEL_NAMES.items():
        history = region_data.get(ch)
        if not history:
            # no data for this channel
            continue

        # pick the newest timestamp; 
        # our build_manifest() sorted ascending, so take the last element
        frame = history[-1]

        files_info.append({
            "slug":      ch,
            "display":   display,
            # wrap each URL in the same structure your template expects:
            "clean":     {"url": frame["clean"],             "thumb": frame["clean"],             "time": frame["time"]},
            "map":       ({"url": frame["map"],               "thumb": frame["map"],               "time": frame["time"]}               if frame.get("map")              else None),
            "enh_clean": ({"url": frame["enhanced_clean"],    "thumb": frame["enhanced_clean"],    "time": frame["time"]} if frame.get("enhanced_clean") else None),
            "enh_map":   ({"url": frame["enhanced_map"],      "thumb": frame["enhanced_map"],      "time": frame["time"]} if frame.get("enhanced_map")   else None),
        })

    return render_template(
        "region.html",
        region_slug= r,
        region_name= REGION_TITLES.get(r, r),
        files_info=  files_info
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
