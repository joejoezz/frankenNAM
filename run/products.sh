#!/bin/bash
# Grid-218 products identical in form to the operational NAM awphys files, from one UPP BGDAWP
# file of the tm06 run (or of the anl reference run, FH0=0: no shift). Mirrors ush/nam_prdgen5.sh (field lists parm/wgrib2.txtlists/nam_awphys*.txt,
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
bk=$RUNDIR/products/buckets; mkdir -p $bk          # the 3 h buckets of every hour, for the 12 h sums
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
$WG $in -s | grep -F -f $LISTS/nam_awphys_inst.txt | grep 'hour fcst' | $WG -i $in -grib inst.g2 > /dev/null || true
touch inst.g2   # MODE=anl f00 (analysis control file): no 'hour fcst' records
$WG $in -s | grep -F -f $LISTS/nam_awphys.txt | $WG -i $in -grib main.g2 > /dev/null

# 2. interpolate to grid 218 (IPOLATES: bilinear, neighbor for categorical/soil fields, budget for accumulations)
[ -s inst.g2 ] && $WG inst.g2 -set_bitmap 1 -set_grib_type c3 -new_grid_winds grid -new_grid_vectors "$VEC" \
    -new_grid_interpolation bilinear -new_grid $GRID218 inst218.g2 > /dev/null
touch inst218.g2
$WG main.g2 -new_grid_vectors "$VEC" -submsg_uv main.uv > /dev/null
$WG main.uv -set_bitmap 1 -set_grib_type c3 -new_grid_winds grid -new_grid_vectors "$VEC" \
    -new_grid_interpolation bilinear \
    -if "$NEIGHBOR" -new_grid_interpolation neighbor -fi \
    -if "$BUDGET" -new_grid_interpolation budget -fi \
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
  $WG all218.g2 -match ":(APCP|ACPCP|WEASD):surface:[0-9]+-[0-9]+ hour acc fcst:" -rpn 0 -set_ftime2 "0-0 day acc fcst" -set_date $CYCLE -set_grib_type c3 -grib_out acc.g2 > /dev/null
  touch acc.g2   # MODE=anl f00 (analysis control): UPP writes no accumulations
else
  # the 3 h bucket of this file (APCP, ACPCP, WEASD in that order), product-clock labelled, kept aside
  $WG all218.g2 -match ":(APCP|ACPCP|WEASD):surface:[0-9]+-[0-9]+ hour acc fcst:" \
      -set_ftime2 "$((10#$ph - PCPBUCKET))-$((10#$ph)) hour acc fcst" -set_date $CYCLE -set_grib_type c3 -grib_out b3.g2 > /dev/null
  [ $($WG b3.g2 -s | wc -l) = 3 ] || { echo "expected APCP/ACPCP/WEASD buckets in $in, got: $($WG b3.g2 -s)"; exit 1; }
  cp b3.g2 $bk/f$ph.g2
  # the 12 h bucket: this 3 h bucket + the earlier ones since b0. wgrib2 cannot add across files in one
  # pass, so each earlier bucket comes in through -import_bin and -rpn adds it
  cp b3.g2 sum.g2
  for q in $(seq $((b0 + PCPBUCKET)) $PCPBUCKET $((10#$ph - PCPBUCKET))); do
    qq=$(printf %02d $q); prev=$bk/f$qq.g2
    [ -s $prev ] || { echo "missing earlier bucket $prev for the 12 h sum"; exit 1; }
    rm -f sum2.g2
    for r in 1 2 3; do
      $WG $prev -d $r -no_header -bin prev$r.bin > /dev/null
      $WG sum.g2 -d $r -rpn "sto_1" -no_header -import_bin prev$r.bin -rpn "rcl_1:+" -set_grib_type c3 -append -grib_out sum2.g2 > /dev/null   # -no_header on both sides: the bin file has no Fortran record headers
    done
    mv sum2.g2 sum.g2
  done
  $WG sum.g2 -set_ftime2 "$b0-$((10#$ph)) hour acc fcst" -set_date $CYCLE -set_grib_type c3 -grib_out b12.g2 > /dev/null
  if [ $b0 -eq $((10#$ph - PCPBUCKET)) ]; then cat b12.g2 > acc.g2            # first hour of a bucket: the 12 h record is the 3 h one
  else $WG b3.g2 -not ":WEASD:" -grib b3nosnow.g2 > /dev/null; cat b12.g2 b3nosnow.g2 > acc.g2; fi   # as the archive: 3 h APCP/ACPCP, no 3 h WEASD
fi

# 4. the clock: reference time C, forecast hour h-6 (verification times unchanged). Every distinct
#    forecast-time string in the file is shifted by -FH0 h: "N hour fcst" -> "N-6 hour fcst" (or anl),
#    "a-b hour max/min/acc/ave fcst" -> "(a-6)-(b-6) ...". Product f00: instantaneous fields become
#    "anl" and the 1 h max/min records are dropped (the archive's f00 file has none).
if [ $((10#$ph)) -eq 0 ]; then
  $WG rest218.g2 -not ":[0-9]+-[0-9]+ hour (max|min) fcst:" -grib rest_f0.g2 > /dev/null; mv rest_f0.g2 rest218.g2
fi
shift_ftime() { # shift_ftime "<ftime string>" -> the same string FH0 hours earlier
  local a b rest
  if [ "$FH0" = 0 ]; then echo "$1"   # MODE=anl: no shift (its f00 also carries "anl" and "0-0 day acc" times)
  elif [[ $1 =~ ^([0-9]+)\ hour\ fcst$ ]]; then
    a=$(( ${BASH_REMATCH[1]} - FH0 )); [ $a -eq 0 ] && echo anl || echo "$a hour fcst"
  elif [[ $1 =~ ^([0-9]+)-([0-9]+)\ hour\ (.*)$ ]]; then
    a=$(( ${BASH_REMATCH[1]} - FH0 )); b=$(( ${BASH_REMATCH[2]} - FH0 )); rest=${BASH_REMATCH[3]}
    [ $a -ge 0 ] || { echo "cannot shift '$1' onto the C clock" >&2; return 1; }
    echo "$a-$b hour $rest"
  else echo "unexpected forecast time '$1'" >&2; return 1; fi
}
args=()
while read -r k; do
  [ -n "$k" ] || continue
  nk=$(shift_ftime "$k") || exit 1
  args+=(-if ":$k:" -set_ftime2 "$nk" -fi)
done < <($WG rest218.g2 -s | cut -d: -f6 | sort -u)
$WG rest218.g2 -set_date $CYCLE "${args[@]}" -set_grib_type c3 -grib_out main_c.g2 > /dev/null
cp acc.g2 acc_c.g2   # accumulations were labelled on the C clock in step 3
# the archive's order: the main list first, then the instantaneous list, accumulations last
cat main_c.g2 acc_c.g2 > $out.tmp
# every record must carry reference time C and verify at START+fh; anything else is a bug, not a product
vt=$(date -u -d "${START:0:8} ${START:8:2}:00 UTC $((10#$fh)) hours" +%Y%m%d%H)
bad=$($WG $out.tmp -s -vt | grep -v ":d=$CYCLE:.*:vt=$vt" | head -3 || true)
[ -z "$bad" ] || { echo "records not on the C clock / wrong verification time: $bad"; exit 1; }
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
