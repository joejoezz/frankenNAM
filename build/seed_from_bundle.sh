#!/bin/bash
# Seed a fresh arm64 build box from the newest runner bundle: unpack the compiled library stack
# (/opt/nam/libs, with libs.sh's .built stamps) and the static files (/opt/nam/fix). libs.sh then
# skips all 22 libraries, so build_all.sh only compiles NPS, NEMS and UPP.
# usage: build/seed_from_bundle.sh            (newest runner/bundle-*-arm64.tar)
#        BUNDLE=bundle-20261106-tm06-arm64.tar build/seed_from_bundle.sh
#        PARTS="fix" build/seed_from_bundle.sh     (static files only, for a from-source library build)
set -euo pipefail
BUCKET=nam-recast-617711905691
BUNDLE=${BUNDLE:-$(aws s3 ls s3://$BUCKET/runner/ | awk '/bundle-.*-arm64\.tar$/{print $4}' | sort | tail -1)}
[ "$(uname -m)" = aarch64 ] || { echo "arm64 bundles only; on x86 run build_all.sh from scratch" >&2; exit 1; }
sudo mkdir -p /opt/nam && sudo chown "$(id -u):$(id -g)" /opt/nam
echo "seeding /opt/nam/{${PARTS:-libs fix}} from s3://$BUCKET/runner/$BUNDLE"
PARTS=${PARTS:-libs fix}
MEMBERS=(); for p in $PARTS; do MEMBERS+=(opt/nam/$p); done
aws s3 cp --only-show-errors s3://$BUCKET/runner/"$BUNDLE" - | tar xf - -C / "${MEMBERS[@]}"
for p in $PARTS; do echo "$BUNDLE" > /opt/nam/$p/.seeded_from; du -sh /opt/nam/$p; done
