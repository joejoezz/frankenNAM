#!/usr/bin/env bash
# Publish the site to s3://nam-recast-site-617711905691 behind CloudFront (deploy/08-site.sh makes both).
#   bash deploy/09-publish-site.sh            # preview: robots.txt blocks crawlers (the default until launch)
#   LAUNCH=1 bash deploy/09-publish-site.sh   # launch: crawlers allowed
# Builds the pages, assembles them with the viewer and the sample frames (frames are copied, not symlinked),
# syncs with --delete, and invalidates CloudFront. Pages and JSON cache 5 min; frames and images 1 day.
# grids/ is NOT touched (excluded from the sync and from --delete): deploy/12-publish-grids.sh owns it.
# Laptop-only for the mockup stage: in Phase 2 the runner publishes frames and runs.js itself.
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET=nam-recast-site-617711905691
read -r DIST CF < deploy/.site-dist
STAGE=$(mktemp -d); trap 'rm -rf "$STAGE"' EXIT
sh site/gen/assemble.sh "$STAGE/link" >/dev/null
cp -RL "$STAGE/link" "$STAGE/www"
if [ "${LAUNCH:-0}" = 1 ]; then printf 'User-agent: *\nAllow: /\n' > "$STAGE/www/robots.txt"
else printf 'User-agent: *\nDisallow: /\n' > "$STAGE/www/robots.txt"; fi
find "$STAGE/www" -name .DS_Store -delete
# Images cache for a day in browsers, so a changed chart must get a new URL: tag every img/ and assets/ reference
# in the pages with a short hash of the file (img/x.png -> img/x.png?v=1a2b3c4d).
python3 - "$STAGE/www" <<'PY'
import hashlib, os, re, sys
root = sys.argv[1]
def tag(m):
    f = os.path.join(root, m.group(2))
    if not os.path.isfile(f): return m.group(0)
    return f'{m.group(1)}{m.group(2)}?v={hashlib.md5(open(f, "rb").read()).hexdigest()[:8]}{m.group(3)}'
for d, _, fs in os.walk(root):
    for n in fs:
        if not n.endswith(".html") or "frames" in d: continue
        p = os.path.join(d, n); t = open(p).read()
        u = re.sub(r'((?:src|href)=")/?((?:img|assets)/[^"?#]+)(")', tag, t)
        if u != t: open(p, "w").write(u)
PY
echo "== $(du -sh "$STAGE/www" | cut -f1) to s3://$BUCKET"
aws s3 sync "$STAGE/www" "s3://$BUCKET" --delete --only-show-errors --exclude "*" \
  --include "*.png" --include "*.jpg" --include "*.svg" --include "*.ico" --exclude "grids/*" --cache-control "public, max-age=86400"
aws s3 sync "$STAGE/www" "s3://$BUCKET" --delete --only-show-errors --exclude "*.png" --exclude "*.jpg" --exclude "*.svg" --exclude "*.ico" --exclude "grids/*" \
  --cache-control "public, max-age=300"
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" --query Invalidation.Id --output text >/dev/null
echo "published: https://$CF/  (and https://nam.theconvergencezone.com/ once its CNAME is live)"
