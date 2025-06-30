#!/usr/bin/env bash
# generate_goes19_dashboard.sh

# 1) Where your GOES-19 output lives:
BASE="/home/jeff/weather/output/goes19"

# 2) Where to write the HTML
OUT="/var/www/html/goes19_dashboard.html"

# 3) A placeholder image if a channel has no data
PLACEHOLDER="/var/www/html/no-data.png"

# 4) List of channels to show
CHANNELS=( ch01 ch02 ch03 ch04 ch05 ch06 ch07 ch08 ch09 ch10 ch11 ch12 ch13 ch14 ch15 ch16 FC )

cat > "$OUT" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GOES-19 Dashboard</title>
  <style>
    body { background: #111; color: #eee; font-family: sans-serif; }
    .grid { display: flex; flex-wrap: wrap; gap: 1rem; }
    .cell { width: 300px; text-align: center; }
    .cell img { max-width: 100%; border: 1px solid #444; }
    .stamp { font-size: 0.8rem; color: #999; }
  </style>
</head>
<body>
  <h1>GOES-19 Dashboard</h1>
  <div class="grid">
EOF

for ch in "${CHANNELS[@]}"; do
  DIR="$BASE/$ch"
  # find newest jpg (by name or mtime)
  latest=$( find "$DIR" -maxdepth 1 -type f -iname '*.jpg' \
               -printf '%T@ %p\n' 2>/dev/null \
             | sort -nr | head -1 | cut -d' ' -f2- )

  if [[ -n "$latest" ]]; then
    # extract the timestamp from the filename if of form ...T%H%M%SZ
    fname=$(basename "$latest")
    if [[ "$fname" =~ ([0-9]{8}T[0-9]{6}Z) ]]; then
      stamp="${BASH_REMATCH[1]}"
    else
      # fallback to file mtime
      stamp=$(date -u -r "$latest" +'%Y-%m-%dT%H:%M:%SZ')
    fi
    img_path="${latest#/var/www/html/}"  # adjust if your webroot differs
  else
    stamp="no data"
    img_path="${PLACEHOLDER#/var/www/html/}"
  fi

  cat >> "$OUT" <<EOF
    <div class="cell">
      <h3>Channel $ch</h3>
      <img src="/$img_path" alt="ch$ch">
      <div class="stamp">$stamp</div>
    </div>
EOF
done

cat >> "$OUT" <<'EOF'
  </div>
</body>
</html>
EOF

echo "Dashboard generated to $OUT"
