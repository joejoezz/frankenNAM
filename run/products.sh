#!/bin/bash
# Grid-218 products identical in form to the operational NAM awphys files, from one UPP BGDAWP
# file of the tm06 run. Mirrors ush/nam_prdgen5.sh (field lists parm/wgrib2.txtlists/nam_awphys*.txt,
# bilinear/neighbor/budget choices, -new_grid_winds grid, submsg U/V pairs, c3 packing) and
# nam_makeprecip (3 h buckets), then rewrites the clock: reference time C, forecast hour h-6.
#
# usage: products.sh <integration hour>      (called by recast.sh stage_post after each UPP file)
# env from recast.sh: CYCLE START RUNDIR PARM HERE cyc pcyc FH0 PCPBUCKET; S3PROD=s3://.../products (optional)
#      WG=wgrib2 (needs IPOLATES with NCEP rotated lat-lon support, USE_IPOLATES=1)
# out: $RUNDIR/products/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2 (+ .idx), uploaded to $S3PROD/nam.YYYYMMDD/
set -euo pipefail
fh=$(printf %02d $((10#$1)))                   # integration hour
ph=$(printf %02d $((10#$fh - FH0)))            # product forecast hour
WG=${WG:-wgrib2}
PDY=${CYCLE:0:8}
LISTS=$PARM/wgrib2.txtlists
in=$RUNDIR/grib2/nam.t${pcyc}z.bgdawp${fh}.tm00.grib2
od=$RUNDIR/products/nam.$PDY; mkdir -p $od $RUNDIR/products/work
out=$od/nam.t${cyc}z.awphys${ph}.tm00.grib2
w=$RUNDIR/products/work/f$ph; rm -rf $w; mkdir -p $w; cd $w
t0=$SECONDS
tl() { echo "$(date -u +%FT%TZ) $*" >> $RUNDIR/timeline.txt; }

GRID218="lambert:265:25:25 226.541:614:12191 12.190:428:12191"   # nam_prdgen5.sh gridspecs
VEC="UGRD:VGRD:USTM:VSTM"
# neighbor / budget sets exactly as wgrib2_parm_filter.py derives them for nam_awphys.txt
NEIGHBOR=$(python3 - "$LISTS/neighbor_interp.parm" "$LISTS/forpyscript/nam_awphys.txt" <<'EOF'
import sys
ex = lambda f: {l.split('(',1)[1].split(')')[0] for l in open(f) if '(' in l}
print("|".join(sorted(ex(sys.argv[1]) & ex(sys.argv[2]))))
EOF
)
BUDGET="APCP|NCPCP|ACPCP|SNOD|WEASD"   # LSPA is not in awphys

# 1. field selection as nam_prdgen5.sh: the instantaneous versions of TCDC/fluxes (nam_awphys_inst.txt,
#    'hour fcst' lines) and the main list (nam_awphys.txt), which also carries the bucketed APCP/ACPCP/WEASD
$WG $in -s | grep -F -f $LISTS/nam_awphys_inst.txt | grep 'hour fcst' | $WG -i $in -grib inst.g2 > /dev/null
$WG $in -s | grep -F -f $LISTS/nam_awphys.txt | $WG -i $in -grib main.g2 > /dev/null

# 2. interpolate to grid 218 (IPOLATES: bilinear, neighbor for categorical/soil fields, budget for accumulations)
$WG inst.g2 -set_bitmap 1 -set_grib_type c3 -new_grid_winds grid -new_grid_vectors "$VEC" \
    -new_grid_interpolation bilinear -new_grid $GRID218 inst218.g2 > /dev/null
$WG main.g2 -new_grid_vectors "$VEC" -submsg_uv main.uv > /dev/null
$WG main.uv -set_bitmap 1 -set_grib_type c3 -new_grid_winds grid -new_grid_vectors "$VEC" \
    -new_grid_interpolation bilinear \
    -if ":($NEIGHBOR):" -new_grid_interpolation neighbor -fi \
    -if ":($BUDGET):" -new_grid_interpolation budget -fi \
    -new_grid $GRID218 main218.uv > /dev/null
$WG main218.uv -new_grid_vectors "$VEC" -submsg_uv main218.g2 > /dev/null
cat main218.g2 inst218.g2 > all218.g2

# 3. accumulations on the product clock. The run carries PCPBUCKET-hour (3 h) buckets; the NAM file
#    carries the 12 h bucket of the C clock (APCP, ACPCP and the snowfall WEASD accumulation) plus,
#    except at the first hour of a bucket, a 3 h APCP/ACPCP (nam_makeprecip). Rebuilt by summing the
#    3 h buckets of this and the earlier product files (already on grid 218, so sums commute with the
#    budget interpolation).
b0=$(( ((10#$ph - 1) / 12) * 12 )); [ $((10#$ph)) -le 0 ] && b0=0        # start of the 12 h bucket on the C clock
$WG all218.g2 -not ":(APCP|ACPCP|WEASD):surface:[0-9]+-[0-9]+ hour acc fcst:" -grib rest218.g2 > /dev/null
if [ $((10#$ph)) -eq 0 ]; then
  # product f00: the archive carries zero-length accumulations (0-0 day acc) with zeros
  $WG all218.g2 -match ":(APCP|ACPCP|WEASD):surface:[0-9]+-[0-9]+ hour acc fcst:" -rpn 0 -set_ftime2 "0-0 day acc fcst" -grib_out acc.g2 > /dev/null
else
  # the 3 h bucket of this file, product-clock labelled
  $WG all218.g2 -match ":(APCP|ACPCP|WEASD):surface:[0-9]+-[0-9]+ hour acc fcst:" \
      -set_ftime2 "$((10#$ph - PCPBUCKET))-$((10#$ph)) hour acc fcst" -grib_out b3.g2 > /dev/null
  # the 12 h bucket: this 3 h bucket + the earlier ones since b0 (taken from the earlier product files,
  # whose 3 h records are the ones labelled "(h-3)-h hour acc")
  cp b3.g2 sum.g2
  for q in $(seq $((b0 + PCPBUCKET)) $PCPBUCKET $((10#$ph - PCPBUCKET))); do
    qq=$(printf %02d $q); prev=$od/nam.t${cyc}z.awphys${qq}.tm00.grib2
    [ -s $prev ] || { echo "missing earlier product $prev for the 12 h bucket"; exit 1; }
    $WG $prev -match ":(APCP|ACPCP|WEASD):surface:$((q - PCPBUCKET))-$q hour acc fcst:" -grib prev.g2 > /dev/null
    # same record order in both files (APCP, ACPCP, WEASD); wgrib2 cannot add across files in one
    # pass, so the earlier bucket's values come in through -import_bin and -rpn adds them
    rm -f sum2.g2
    for r in 1 2 3; do
      $WG prev.g2 -d $r -no_header -bin prev$r.bin > /dev/null
      $WG sum.g2 -d $r -rpn "sto_1" -import_bin prev$r.bin -rpn "rcl_1:+" -append -grib_out sum2.g2 > /dev/null
    done
    mv sum2.g2 sum.g2
  done
  $WG sum.g2 -set_ftime2 "$b0-$((10#$ph)) hour acc fcst" -grib_out b12.g2 > /dev/null
  if [ $b0 -eq $((10#$ph - PCPBUCKET)) ]; then cat b12.g2 > acc.g2            # first hour of a bucket: the 12 h record is the 3 h one
  else $WG b3.g2 -not ":WEASD:" -grib b3nosnow.g2 > /dev/null; cat b12.g2 b3nosnow.g2 > acc.g2; fi   # as the archive: 3 h APCP/ACPCP, no 3 h WEASD
fi

# 4. the clock: reference time C, forecast hour h-6 (verification times unchanged); instantaneous
#    fields at product f00 become "anl"; the 3 h max/min records are not in the archive's f00 file
if [ $((10#$ph)) -eq 0 ]; then
  $WG rest218.g2 -not ":[0-9]+-[0-9]+ hour (max|min) fcst:" -set_date $CYCLE -set_ftime2 anl -grib_out main_c.g2 > /dev/null
  $WG acc.g2 -set_date $CYCLE -grib_out acc_c.g2 > /dev/null
else
  $WG rest218.g2 -set_date $CYCLE -if ":${fh#0} hour fcst:" -set_ftime2 "${ph#0} hour fcst" -fi \
      -if ":$((10#$fh - 3))-${fh#0} hour max fcst:" -set_ftime2 "$((10#$ph - 3))-${ph#0} hour max fcst" -fi \
      -if ":$((10#$fh - 3))-${fh#0} hour min fcst:" -set_ftime2 "$((10#$ph - 3))-${ph#0} hour min fcst" -fi \
      -grib_out main_c.g2 > /dev/null
  $WG acc.g2 -set_date $CYCLE -grib_out acc_c.g2 > /dev/null   # ftime already on the C clock
fi
# any record whose reference time did not move to C is a bug, not a product
bad=$($WG main_c.g2 acc_c.g2 -s 2>/dev/null | grep -v ":d=$CYCLE:" | head -3 || true)
[ -z "$bad" ] || { echo "records not on the C clock: $bad"; exit 1; }
# the archive's order: the main list first, then the instantaneous list, accumulations last
cat main_c.g2 acc_c.g2 > $out.tmp
mv $out.tmp $out
$WG -s $out > $out.idx
n=$($WG -s $out | wc -l)
echo "products f$ph: $n records, $((SECONDS - t0)) s"
tl "products f$ph done ($n records)"
if [ -n "${S3PROD:-}" ]; then
  aws s3 cp --only-show-errors $out $S3PROD/nam.$PDY/ && aws s3 cp --only-show-errors $out.idx $S3PROD/nam.$PDY/
  tl "products f$ph uploaded"
fi
cd /; rm -rf $w
