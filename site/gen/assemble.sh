#!/bin/sh
# Assemble the mockup into a folder outside the repo and print how to open it.
#   sh site/gen/assemble.sh [OUTDIR]      default ~/data/nam-recast-site/mockup
# Pages at the root, the viewer and its frames under maps/ (frames are symlinked, not copied).
set -e
SITE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/data/nam-recast-site/mockup}"
FRAMES="${FRAMES:-$HOME/data/nam-recast-site/out}"     # site/render output with both models
python3 "$SITE/gen/build_pages.py" >/dev/null
rm -rf "$OUT"; mkdir -p "$OUT/maps" "$OUT/assets"
cp -R "$SITE"/pages/. "$OUT"/
cp "$SITE/assets/nam-logo.png" "$OUT/assets/"
cp "$SITE/viewer/index.html" "$OUT/maps/index.html"
cp "$FRAMES/runs.js" "$FRAMES/runs.json" "$OUT/maps/"
ln -s "$FRAMES/frames" "$OUT/maps/frames"
echo "open $OUT/index.html"
