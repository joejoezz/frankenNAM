#!/bin/bash
# GPU-node driver (optional engine for FrankenNAM): WOOF-NAM on one GPU, tm06 shape, then our NOAA-named product.
# Runs on the instance only (third-party code never runs on the laptop). Started by deploy/11-gpu-runner.sh's user-data.
#
#   install (pinned commit, bootstrap at boot) -> fetch GFS (start cycle S = C-6 h, boundaries from the SAME cycle,
#   --boco-age 0) -> static -> init saved without TDFI -> Noah soil seed edited into the saved init (seed_init.py)
#   -> woof-nam run --init-from (TDFI, 90 h) with a products follower on the 3-hourly hours -> restamp.py per hour
#   (clock moved to C, NOAA names, .idx) -> upload each product when its .idx exists -> DONE/FAILED markers.
#
# env: CYCLE (product cycle, YYYYMMDDHH; required)   HOURS (integration length, default 90 = f84; a short test: 12)
#      SEED_S3 (soil seed grib2; default cases/$CYCLE/seed/nam.t<SS>z.awphys00.tm00.grib2, live: the previous cycle's
#               own awphys06 product)   RUNTAG (default run: prefix cases/$CYCLE/gpu/$RUNTAG for logs/markers)
#      S3PROD (product prefix; default cases/$CYCLE/gpu/$RUNTAG/products. The acceptance/live value is
#              s3://nam-recast-617711905691/products-gpu/nam.YYYYMMDD)
#      COMMIT (woof-nam pin)  HOLD_ON_FAIL=1 (sleep instead of exiting when a stage fails, for ssh debugging)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
: "${CYCLE:?CYCLE=YYYYMMDDHH}"
HOURS=${HOURS:-90}; LAG=6
COMMIT=${COMMIT:-49f2742914db48a24f0bb9122383aadb57ad1ebd}
BUCKET=nam-recast-617711905691
RUNTAG=${RUNTAG:-run}
S3CASE=s3://$BUCKET/cases/$CYCLE/gpu/$RUNTAG
S3PROD=${S3PROD:-$S3CASE/products}
START=$(date -u -d "${CYCLE:0:8} ${CYCLE:8:2}:00 UTC - $LAG hours" +%Y%m%d%H)
CASE=$(date -u -d "${START:0:8} ${START:8:2}:00 UTC" +%Y-%m-%d_%Hz)
SS=${START:8:2}
SEED_S3=${SEED_S3:-s3://$BUCKET/cases/$CYCLE/seed/nam.t${SS}z.awphys00.tm00.grib2}
W=${W:-$HOME/woof}; mkdir -p $W; cd $W
LOG=$W/gpu-runner.log; TL=$W/timeline.txt
OUT=$W/runs/tm06
WG=$W/wg/bin/wgrib2
tl() { echo "$(date -u +%FT%TZ) $*" | tee -a $TL; }
push_logs() { for f in gpu-runner.log timeline.txt run.log fetch.log init.log seed.log products.log ship.log static.log install.log; do
                [ -s $W/$f ] && aws s3 cp --only-show-errors $W/$f $S3CASE/logs/$f; done
              for f in forecast-receipt.json timing_receipt.json; do [ -s $OUT/$f ] && aws s3 cp --only-show-errors $OUT/$f $S3CASE/logs/$f; done; true; }
fail() { tl "FAILED: $*"; echo "$*" | aws s3 cp --only-show-errors - $S3CASE/FAILED; push_logs
         [ "${HOLD_ON_FAIL:-0}" = 1 ] && { tl "holding for ssh (HOLD_ON_FAIL=1); the shutdown failsafe ends it"; sleep 100000; }
         exit 1; }
trap 'push_logs' EXIT
exec > >(tee -a $LOG) 2>&1
aws s3 rm --only-show-errors $S3CASE/DONE $S3CASE/FAILED 2>/dev/null || true   # (rm of a missing key is silent)
tl "gpu runner start C=$CYCLE start=$START case=$CASE hours=$HOURS commit=${COMMIT:0:8} $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null) $(curl -s -m 2 http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null)"

# ---------------------------------------------------------------- install
tl "install"
(
  set -e
  [ -d src ] || git clone -q https://github.com/recastsystems/woof-nam.git src
  git -C src checkout -q $COMMIT
  [ -d venv ] || python3 -m venv venv
  . venv/bin/activate
  pip install -q ./src eccodes
  # 30-arcsec GMTED2010 terrain (1.9 GB, ~11 s): init-gwd-orog refuses to run without it, whatever the source
  [ -d $HOME/WPS_GEOG/topo_gmted2010_30s ] || gpuwm fetch-geog --datasets topo_gmted2010_30s --root $HOME/WPS_GEOG
) > install.log 2>&1 || { tail -20 install.log; fail "install"; }
( # wgrib2 (conda-forge build) for the .idx files, in the background while the data fetch runs
  curl -fsL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C $W bin/micromamba &&
  $W/bin/micromamba create -y -q -p $W/wg -c conda-forge wgrib2 ) > wg.log 2>&1 &
WGPID=$!
. venv/bin/activate
export NAMGPU_ROOT=$W NAMGPU_BOCO_AGE_H=0       # boundaries from the start cycle itself (tm06: start and boundaries are one GFS cycle)
tl "installed woof-nam $(pip list 2>/dev/null | awk '/woof-nam/{print $2}')"

# ---------------------------------------------------------------- fetch
tl "fetch GFS $START f000..f$(printf %03d $((HOURS+6)))"
woof-nam fetch --cycle $START --hours $HOURS --case-dir cases/$CASE --source gfs --gfs-only --inputs-only --boco-age 0 > fetch.log 2>&1 \
  || { tail -20 fetch.log; fail "fetch"; }
tail -2 fetch.log
tl "static"
python - > static.log 2>&1 <<PY || { tail -20 static.log; fail "static"; }
from datetime import datetime
from pathlib import Path
from namgpu import domains, paths
domains.select(None, "gfs")
st = datetime.strptime("$CASE"[:13], "%Y-%m-%d_%H")
print(domains.ensure_static(paths.case_dir("$CASE"), st, "gfs"))
PY
cat static.log

# ---------------------------------------------------------------- init (no TDFI), seed, run
tl "init (slab_init save, no TDFI)"
python -m namgpu.init.slab_init save --case $CASE --source gfs --hours $HOURS --out $W/init > init.log 2>&1 \
  || { tail -30 init.log; fail "init"; }
tail -3 init.log
tl "init saved $(du -sh $W/init | cut -f1)"
aws s3 cp --only-show-errors $SEED_S3 $W/seed.grib2 || fail "seed download $SEED_S3"
tl "seed the Noah state from $SEED_S3"
python $HERE/seed_init.py $W/init $W/seed.grib2 > seed.log 2>&1 || { tail -30 seed.log; fail "seed"; }
cat seed.log
aws s3 cp --only-show-errors $W/init/seed-receipt.json $S3CASE/logs/seed-receipt.json

wait $WGPID; [ -x $WG ] || { tail -5 wg.log; fail "wgrib2 install"; }
tl "wgrib2 $($WG -version 2>&1 | head -1)"
PRODHOURS=$(seq -s, 6 3 $HOURS)
mkdir -p $OUT
python -c "import sys; sys.path.insert(0,'$W/src'); from namgpu.io.products import main; sys.exit(main(sys.argv[1:]))" \
  --run $OUT --out $OUT/products --follow --hours $PRODHOURS > products.log 2>&1 &
FOLLOWPID=$!
tl "run: TDFI + $HOURS h"
woof-nam run --case $CASE --source gfs --hours $HOURS --init-from $W/init --out $OUT --no-maps --no-columns > run.log 2>&1 &
RUNPID=$!

# ---------------------------------------------------------------- ship: restamp + upload each product when complete
SHIPRC=0
ship() {
  local ii fh raw tries
  for ii in $(seq 6 3 $HOURS); do
    fh=$((ii - LAG)); raw=$OUT/products/woof-nam.t${SS}z.awphys$(printf %02d $ii).tm00.grib2
    tries=0
    until [ -f $raw.idx ]; do      # their completion signal: the .idx lands whole and last
      kill -0 $FOLLOWPID 2>/dev/null || { [ -f $raw.idx ] && break; echo "follower gone before $raw.idx"; return 1; }
      sleep 5
    done
    mkdir -p $W/product
    python $HERE/restamp.py --raw $OUT/products --out $W/product --cycle $CYCLE --hours $fh --wgrib2 $WG || { echo "restamp f$fh failed"; return 1; }
    f=$W/product/nam.t${CYCLE:8:2}z.awphys$(printf %02d $fh).tm00.grib2
    aws s3 cp --only-show-errors $f $S3PROD/$(basename $f) && aws s3 cp --only-show-errors $f.idx $S3PROD/$(basename $f).idx \
      || { echo "upload f$fh failed"; return 1; }
    echo "$(date -u +%FT%TZ) shipped f$(printf %02d $fh) ($(stat -c %s $f) bytes, $(wc -l < $f.idx) records)"
  done
}
ship > ship.log 2>&1 &
SHIPPID=$!
( while kill -0 $RUNPID 2>/dev/null; do sleep 300; push_logs; done ) &

wait $RUNPID; RRC=$?
tl "run rc=$RRC"
[ $RRC = 0 ] || { tail -30 run.log; }
wait $FOLLOWPID; FRC=$?
tl "product follower rc=$FRC"
wait $SHIPPID; SRC=$?
tl "ship rc=$SRC ($(grep -c shipped ship.log) products shipped)"
tl "run summary: $(grep -E 'init done|tdfi done|ms/step|steps' run.log | tail -4 | tr '\n' ' ')"
if [ $RRC = 0 ] && [ $FRC = 0 ] && [ $SRC = 0 ]; then
  tl "DONE"; echo done | aws s3 cp --only-show-errors - $S3CASE/DONE
else
  fail "run=$RRC follower=$FRC ship=$SRC"
fi
push_logs
