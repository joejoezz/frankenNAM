#!/bin/bash
# Runner-node driver (c7a.48xlarge from the build-box AMI): forecast + post for $CYCLE with
# hourly S3 syncs; resumes from the newest restart in S3 after a Spot interruption.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export CYCLE=${CYCLE:-2026110100}
export RUNDIR=/opt/nam/runs/$CYCLE S3RUN=s3://nam-recast-617711905691/cases/$CYCLE/recast
cd "$HERE"
mkdir -p $RUNDIR/fcst $RUNDIR/grib2
echo "runner start $(date -u +%FT%TZ) $(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null)" | tee -a $RUNDIR/runner.log
aws s3 sync --only-show-errors $S3RUN/history/ $RUNDIR/fcst/ --exclude "*" --include "nmmb_rst_*"
aws s3 sync --only-show-errors $S3RUN/grib2-all/ $RUNDIR/grib2/
./recast.sh fcst > $RUNDIR/fcst.log 2>&1 &
FPID=$!
( while kill -0 $FPID 2>/dev/null; do sleep 3000; ./recast.sh sync >> $RUNDIR/sync.log 2>&1; done ) &
sleep 120
WAIT=1 ./recast.sh post > $RUNDIR/post.log 2>&1; PRC=$?
wait $FPID; FRC=$?
echo "fcst rc=$FRC post rc=$PRC $(date -u +%FT%TZ)" | tee -a $RUNDIR/runner.log
./recast.sh sync >> $RUNDIR/sync.log 2>&1
aws s3 cp --only-show-errors $RUNDIR/runner.log $S3RUN/logs/runner.log
for f in fcst.log post.log sync.log; do aws s3 cp --only-show-errors $RUNDIR/$f $S3RUN/logs/$f; done
[ $FRC = 0 ] && [ $PRC = 0 ] && echo done | aws s3 cp - $S3RUN/DONE || echo "fcst=$FRC post=$PRC" | aws s3 cp - $S3RUN/FAILED
