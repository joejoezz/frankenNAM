#!/usr/bin/env bash
# Publish the free grids of re-run cases under /grids/ of the site (S3 bucket behind CloudFront).
#   bash deploy/12-publish-grids.sh 2026110100 [CASE ...]
# For each case: copy cases/<CASE>/products/nam.YYYYMMDD/ into s3://<site bucket>/grids/ server-side (no data
# leaves S3; us-west-2 to us-west-2), then rebuild the index pages with site/gen/grid_index.py over everything that
# is in grids/ and upload them (index.html, status.json, nam.YYYYMMDD/index.html, cycle.json). SHA-256 hashes are
# computed by streaming each new object once (a few cents of transfer to this machine); they are cached in
# $HASHDIR so a rerun hashes only new files. Cache: 1 day. Never touches anything outside grids/.
# Does not read or write the hindcast cases' products unless you name them: name a case only when its rerun is done.
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 CASE [CASE ...]   (CASE = YYYYMMDDHH, e.g. 2026110100)"; exit 1; }
REGION=us-west-2
SRC=nam-recast-617711905691
SITE=nam-recast-site-617711905691
read -r DIST CF < deploy/.site-dist
HASHDIR=${HASHDIR:-$HOME/data/nam-recast-site/grids-index}
OUT=$(mktemp -d); trap 'rm -rf "$OUT"' EXIT
mkdir -p "$HASHDIR"; [ -f "$HASHDIR/sha256.json" ] && cp "$HASHDIR/sha256.json" "$OUT/"
CC="public, max-age=86400"
for C in "$@"; do
  P="s3://$SRC/cases/$C/products"
  aws s3 ls --region $REGION "$P/" | grep -q 'PRE nam\.' || { echo "no nam.YYYYMMDD/ under $P/"; exit 1; }
  for D in $(aws s3 ls --region $REGION "$P/" | awk '/PRE nam\./ {print $2}'); do
    echo "== $C: $D"
    # GRIB2 first, then the .idx (an .idx is the signal that an hour is ready), each with its content type
    aws s3 cp --region $REGION --recursive "$P/$D" "s3://$SITE/grids/$D" --only-show-errors --exclude "*" --include "*.grib2" \
      --metadata-directive REPLACE --cache-control "$CC" --content-type application/octet-stream
    aws s3 cp --region $REGION --recursive "$P/$D" "s3://$SITE/grids/$D" --only-show-errors --exclude "*" --include "*.idx" \
      --metadata-directive REPLACE --cache-control "$CC" --content-type text/plain
  done
done
# index pages over everything now in grids/ (all cases, not only these): 10 years back so old cases stay listed
python3 site/gen/grid_index.py --src "s3://$SITE/grids" --region $REGION --out "$OUT" --up 1 --window-days 3650
cp "$OUT/sha256.json" "$HASHDIR/sha256.json"
rm "$OUT/sha256.json"
aws s3 cp --region $REGION --recursive "$OUT" "s3://$SITE/grids" --only-show-errors --cache-control "$CC" \
  --exclude "*" --include "*.html" --content-type text/html
aws s3 cp --region $REGION --recursive "$OUT" "s3://$SITE/grids" --only-show-errors --cache-control "$CC" \
  --exclude "*" --include "*.json" --content-type application/json
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/grids/*" --query Invalidation.Id --output text >/dev/null
echo "published: https://$CF/grids.html  (files under https://$CF/grids/)"
