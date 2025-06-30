#!/bin/bash
echo "Creating animations..."

for sat in GOES-19 NOAA-15 NOAA-19; do
  if [[ "$sat" == "GOES-19" ]]; then
    for region in FD MESO; do
      for band_dir in static/$sat/$region/CH*; do
        [ -d "$band_dir" ] || continue
        img_count=$(ls "$band_dir"/*.png 2>/dev/null | wc -l)
        if (( img_count > 1 )); then
          convert -delay 20 -loop 0 "$band_dir"/*.png "$band_dir/animation.gif"
          echo "Made $band_dir/animation.gif"
        fi
      done
    done
  else
    apt_dir="static/$sat/APT"
    [ -d "$apt_dir" ] || continue
    img_count=$(ls "$apt_dir"/*.png 2>/dev/null | wc -l)
    if (( img_count > 1 )); then
      convert -delay 20 -loop 0 "$apt_dir"/*.png "$apt_dir/animation.gif"
      echo "Made $apt_dir/animation.gif"
    fi
  fi
done
