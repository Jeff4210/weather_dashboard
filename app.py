#!/usr/bin/env python3
import os, re, glob, threading
import datetime
from zoneinfo import ZoneInfo
from flask import (
    Flask, render_template, send_from_directory, abort,
    url_for, request, current_app, jsonify
)
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────
OUTPUT_BASE = "/home/jeff/weather/output/goes19"
THUMB_BASE = "/home/jeff/weather_dashboard/thumbs"

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

# ─── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__,
            static_folder="static",
            static_url_path="/static",
            template_folder="templates")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ─── Health-check endpoint ────────────────────────────────────────────────────
@app.route("/ping")
def ping():
    return "pong", 200

# ─── Thumbnail generator ──────────────────────────────────────────────────────
def make_thumb(src, size=(600,600), quality=95):
    rel = os.path.relpath(src, OUTPUT_BASE)
    dst = os.path.join(THUMB_BASE, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    # DEBUG
    current_app.logger.debug(f"make_thumb: src={src} dst={dst}")

    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        im = Image.open(src)
        im.thumbnail(size)
        im.save(dst, "JPEG", quality=quality)

    return dst
# ─── In-memory manifest + lock ────────────────────────────────────────────────
_manifest      = {}
_manifest_lock = threading.Lock()

def build_manifest():
    new = {}
    for region in ("fd", "m1", "m2"):
        new[region] = {}
        for channel in CHANNEL_NAMES:
            base = os.path.join(OUTPUT_BASE, region, channel)
            if not os.path.isdir(base):
                continue

            # find date folders
            dates = sorted(
                (d for d in os.listdir(base)
                 if os.path.isdir(os.path.join(base, d))
                 and re.match(r"\d{4}-\d{2}-\d{2}", d)),
                reverse=True
            )

            # ── FALLBACK ── if no date folders, treat base itself as one “date”
            if not dates:
                dates = ['.']

            for d in dates:
                folder = os.path.join(base, d) if d != '.' else base
                files = sorted(glob.glob(f"{folder}/*.*"),
                               key=os.path.getmtime, reverse=True)
                if not files:
                    continue

                tag  = f"_{channel}_"
                imgs = [f for f in files
                        if tag.lower() in os.path.basename(f).lower()]
                if not imgs:
                    continue

                # bucket them...
                buckets = {
                    "clean":     [p for p in imgs if "_enhanced_" not in p.lower() and "_map." not in p.lower()],
                    "map":       [p for p in imgs if "_enhanced_" not in p.lower() and "_map."   in p.lower()],
                    "enh_clean": [p for p in imgs if "_enhanced_"    in p.lower() and "_map." not in p.lower()],
                    "enh_map":   [p for p in imgs if "_enhanced_"    in p.lower() and "_map."   in p.lower()],
                }

                def info(path):
                    fname = os.path.basename(path)
                    # use d for URL even if it was '.'
                    date_for_url = d if d != '.' else datetime.datetime.fromtimestamp(
                        os.path.getmtime(path),
                        tz=ZoneInfo("America/New_York")
                    ).strftime("%Y-%m-%d")
                    return {
                        "url":   url_for("serve_image", region=region, channel=channel,
                                         date=date_for_url, filename=fname),
                        "thumb": url_for("serve_thumb",
                                         filename=os.path.relpath(make_thumb(path), THUMB_BASE)),
                        "time":  datetime.datetime.fromtimestamp(
                                    os.path.getmtime(path),
                                    tz=ZoneInfo("America/New_York")
                                ).strftime("%Y-%m-%d %I:%M %p")
                    }

                out = {}
                for k, lst in buckets.items():
                    if lst:
                        out[k] = info(max(lst, key=os.path.getmtime))

                if out:
                    new[region][channel] = out
                break  # only process the newest “date”
    # swap in manifest as before…
    with _manifest_lock:
        global _manifest
        _manifest = new

@app.route("/")
def index():
    """Render the home page from the in-memory manifest."""
    current_app.logger.info("🟢 index() start")
    with _manifest_lock:
        snapshot = _manifest.copy()
    sections = []
    for region, channels in snapshot.items():
        # look for the FC clean thumbnail for each region
        fc = channels.get("fc", {}).get("clean")
        if not fc:
            continue
        sections.append({
            "slug":  region,
            "label": REGION_TITLES[region],
            "thumb": fc["thumb"],
            "link":  url_for("region_page", region=region)
        })
    current_app.logger.info("🔵 index() end")
    return render_template("index.html", sections=sections)


@app.route("/<region>")
def region_page(region):
    """Render a single-region page from the in-memory manifest."""
    current_app.logger.info(f"🟢 region_page({region}) start")
    r = region.lower()
    with _manifest_lock:
        channels = _manifest.get(r)
    if not channels:
        abort(404)

    files_info = []
    for ch, display in CHANNEL_NAMES.items():
        info = channels.get(ch, {})
        # we require at least a “clean” image
        clean = info.get("clean")
        if not clean:
            continue
        files_info.append({
            "slug":      ch,
            "display":   display,
            "clean":     clean,            # already has url/thumb/time
            "map":       info.get("map"),
            "enh_clean": info.get("enh_clean"),
            "enh_map":   info.get("enh_map"),
        })

    current_app.logger.info(f"🔵 region_page({region}) end")
    return render_template(
        "region.html",
        region_name=REGION_TITLES[r],
        files_info=files_info
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
    """Return the entire in-memory manifest as JSON for debugging."""
    with _manifest_lock:
        # make a shallow copy under lock to avoid races
        snap = dict(_manifest)
    return jsonify(snap)

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
    thumb = make_thumb(src)
    folder, fname = os.path.split(thumb)
    return send_from_directory(folder, fname, mimetype="image/jpeg")

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

# ─── Kick off the initial build and periodic rebuilds (after routes!) ─────────
start_build_loop()

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now}
# ─── Debug entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=True)
