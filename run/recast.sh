#!/bin/bash
# NAM 12 km parent-domain recast: GFS -> NPS -> NEMS.x (NMMB) -> UPP -> grid-218 products.
# Follows exnam_coldstart_prep.sh, exnam_{ungrib,metgrid}_boco.sh, exnam_nemsinterp_boco*.sh,
# exnam_fcst.sh, exnam_post.sh and nam_prdgen5.sh with plain paths and Intel MPI or OpenMPI;
# see run/README.md and docs/tm06-design.md.
#
# usage: recast.sh <stage...>   stages: stage ungrib seed metgrid nemsinterp fcst post products sync  (or: nps, all)
# env:   CYCLE=2026110100 (product cycle C)  MODE=tm06|anl
#          tm06 (default): the model starts at START = C-6 h from GFS cycle C-6 f000, boundaries
#               f003..f090 (3-hourly), integrates 90 h; integration hour 6 is product f00. The Noah
#               land state is seeded through metgrid from a grid-218 NAM-format GRIB2 file valid at
#               START ($SEED, default /opt/nam/cases/$CYCLE/seed/*.grib2; SEED=none disables).
#               3 h precipitation buckets, UPP on hours 6..90, products on the C clock.
#          anl: the Phase 0 analysis start at C from GFS cycle C f000, 84 h, 12 h buckets.
#        FHMAX=90|84 INPES=4 JNPES=7 WRITE_GROUPS=1 WRITE_TASKS=4 NPOST=8
#        RUNDIR=/opt/nam/runs/$CYCLE  S3RUN=s3://.../cases/$CYCLE/recast  FILTER=3
#        RESTMIN=720 RST00=true WRTLAST=true (restarts; RESTMIN=100800 RST00=false WRTLAST=false = none;
#        RESTMIN*60 must be a multiple of the 25 s timestep)  SYNC_HISTORY=1
#        NEMS_EXE=/opt/nam/work/exec/NEMS.x (NEMS_debug.x for the trap build)
#        PRODUCTS=1 (grid-218 awphys files after each UPP file, run/products.sh; tm06 relabelled onto the C
#        clock, anl as is)
#        S3PROD=s3://nam-recast-617711905691/products (where products.sh uploads; empty = no upload)
#        NPS_CLEAN=1 deletes each NPS stage's inputs once the next stage has consumed them (83 GB for 90 h)
#        IC_ONLY=1 makes metgrid/nemsinterp do the initial condition only (re-seeding tests)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)

ndate() { date -u -d "${2:0:8} ${2:8:2}:00 UTC $1 hours" +%Y%m%d%H; }   # ndate <+-h> <yyyymmddhh>
wpsdate() { echo "${1:0:4}-${1:4:2}-${1:6:2}_${1:8:2}"; }
log() { echo "[$(date -u +%T)] $*"; }

CYCLE=${CYCLE:-2026110100}
MODE=${MODE:-tm06}
case $MODE in
  tm06) START=$(ndate -6 $CYCLE); FHMAX=${FHMAX:-90}; PCPBUCKET=${PCPBUCKET:-3}; FH0=6
        GFSDIR=${GFSDIR:-/opt/nam/cases/$CYCLE/gfs-tm06}; SEEDDIR=${SEEDDIR:-/opt/nam/cases/$CYCLE/seed} ;;
  # anl: 3 h precipitation buckets too (Phase 0 had 12 h) so products.sh builds the same grid-218 awphys
  # files with no clock shift (FH0=0); the bucket length only changes when the accumulators reset
  anl)  START=$CYCLE; FHMAX=${FHMAX:-84}; PCPBUCKET=${PCPBUCKET:-3}; FH0=0
        GFSDIR=${GFSDIR:-/opt/nam/cases/$CYCLE/gfs}; SEEDDIR=${SEEDDIR:-}; SEED=${SEED:-none} ;;
  *) echo "MODE must be tm06 or anl"; exit 1 ;;
esac
INPES=${INPES:-4}; JNPES=${JNPES:-7}; WRITE_GROUPS=${WRITE_GROUPS:-1}; WRITE_TASKS=${WRITE_TASKS:-4}
NPOST=${NPOST:-8}
NPS_NP=${NPS_NP:-14}            # ops ran metgrid/nemsinterp on 14 tasks
FILTER=${FILTER:-3}             # ops tm00 free forecast without restart: filter_method 3 (TDFI)
HISTMIN=${HISTMIN:-180}         # history every 3 h (ops parent: 60)
RESTMIN=${RESTMIN:-720}         # restart every 12 h for Spot recovery
NAM_SRC=${NAM_SRC:-/opt/nam/work/src}
EXEC=${EXEC:-/opt/nam/work/exec}
FIX=${FIX:-/opt/nam/fix}
PARM=$NAM_SRC/parm
RUNDIR=${RUNDIR:-/opt/nam/runs/$CYCLE}
S3RUN=${S3RUN:-s3://nam-recast-617711905691/cases/$CYCLE/recast}
S3CASE=${S3CASE:-s3://nam-recast-617711905691/cases/$CYCLE}
cyc=${CYCLE:8:2}                # product cycle hour (file names of the products)
pcyc=${START:8:2}               # GFS / model-start cycle hour (file names of the inputs and UPP output)
export CYCLE MODE START FHMAX PCPBUCKET GFSDIR RUNDIR S3RUN S3CASE cyc pcyc FH0 HERE PARM FIX EXEC NAM_SRC

# toolchain runtime; no module, no prod_util. Intel MPI for the x86/oneAPI build (Phase 0),
# OpenMPI for the arm64/gfortran build (Graviton port): picked by what is installed.
export OMP_NUM_THREADS=1 OMP_STACKSIZE=1G KMP_STACKSIZE=1G
if [ -f /opt/intel/oneapi/setvars.sh ]; then
  MPI=intel
  set +eu; source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1; set -eu
  export I_MPI_FABRICS=${I_MPI_FABRICS:-shm} I_MPI_PIN_DOMAIN=${I_MPI_PIN_DOMAIN:-core}
else
  MPI=openmpi
  export OMPI_MCA_btl=${OMPI_MCA_btl:-self,vader}   # single node: shared memory only, no tcp probing
  # UPP writes GRIB2 with MPI-IO. Both OpenMPI components work (a SIGBUS first blamed on OMPIO
  # was a full disk); ROMIO is kept because the arm64 validation run used it. OMPI_MCA_io= clears it.
  export OMPI_MCA_io=${OMPI_MCA_io-^ompio}
fi
export MPI
ulimit -s unlimited || true
# mpi_cmd <ntasks> <core|none> [cpu list]: the mpirun prefix. Intel MPI pins through
# I_MPI_PIN_DOMAIN/I_MPI_PIN_PROCESSOR_LIST (exported by the callers, as in Phase 0); OpenMPI
# needs explicit --bind-to core (its default for >2 ranks is socket) and --cpu-set for a subset.
mpi_cmd() {
  local n=$1 bind=$2 cpus=${3:-}
  if [ "$MPI" = intel ]; then echo "mpirun -n $n -ppn $n"
  elif [ -n "$cpus" ]; then echo "mpirun -n $n --cpu-set $cpus --bind-to core"   # no --map-by: OpenMPI 4.1 rejects it with a cpu set
  elif [ "$bind" = core ]; then echo "mpirun -n $n --bind-to core --map-by core"
  else echo "mpirun -n $n --bind-to none"; fi
}

mkdir -p "$RUNDIR"; cd "$RUNDIR"
fhrs() { seq -f %02g 0 3 "$FHMAX"; }
tl() { echo "$(date -u +%FT%TZ) $*" >> $RUNDIR/timeline.txt; }   # stage clock (docs/tm06-design.md)

# namelist.nps from a template with YSTART..HEND replaced (exnam_* sed chains)
mk_nps() { # mk_nps <template> <start yyyymmddhh> <end yyyymmddhh>
  local s=$2 e=$3
  sed -e "s:YSTART:${s:0:4}:" -e "s:MSTART:${s:4:2}:" -e "s:DSTART:${s:6:2}:" -e "s:HSTART:${s:8:2}:" \
      -e "s:YEND:${e:0:4}:" -e "s:MEND:${e:4:2}:" -e "s:DEND:${e:6:2}:" -e "s:HEND:${e:8:2}:g" \
      -e "s:IGNORE_GRIDGEN:.false.:" "$1" > namelist.nps
}

seed_file() { # the soil seed GRIB2 for this run, or nothing
  [ "${SEED:-}" = none ] && return 0
  if [ -n "${SEED:-}" ]; then echo "$SEED"; else ls "$SEEDDIR"/*.grib2 2>/dev/null | head -1; fi
}

stage_stage() { # inputs from the case prefix in our bucket; a missing GFS/seed is copied server-side from the NOAA archives first
  local gsrc ssrc h
  tl "stage start"
  mkdir -p "$GFSDIR"
  if [ "$MODE" = tm06 ]; then
    gsrc=$S3CASE/gfs-tm06
    if ! aws s3 ls "$gsrc/gfs.t${pcyc}z.pgrb2.0p25.f$(printf %03d $FHMAX)" >/dev/null 2>&1; then
      log "staging GFS ${START} f000-f$FHMAX from noaa-gfs-bdp-pds into $gsrc (server-side copy)"
      for h in $(seq -f %03g 0 3 $FHMAX); do
        aws s3 cp --only-show-errors --copy-props none s3://noaa-gfs-bdp-pds/gfs.${START:0:8}/${pcyc}/atmos/gfs.t${pcyc}z.pgrb2.0p25.f$h $gsrc/gfs.t${pcyc}z.pgrb2.0p25.f$h &
        (( 10#$h % 12 == 9 )) && wait
      done; wait
    fi
    if [ -z "$(seed_file)" ] && [ -n "$SEEDDIR" ]; then
      mkdir -p "$SEEDDIR"
      ssrc=$S3CASE/seed
      if ! aws s3 ls "$ssrc/" 2>/dev/null | grep -q grib2; then   # hindcast default: the archived NAM analysis of the start cycle
        log "staging the soil seed nam.t${pcyc}z.awphys00.tm00.grib2 of ${START:0:8} from noaa-nam-pds"
        aws s3 cp --only-show-errors --copy-props none s3://noaa-nam-pds/nam.${START:0:8}/nam.t${pcyc}z.awphys00.tm00.grib2 $ssrc/nam.t${pcyc}z.awphys00.tm00.grib2
      fi
      aws s3 sync --only-show-errors "$ssrc/" "$SEEDDIR/"
    fi
  else
    gsrc=$S3CASE/gfs
  fi
  aws s3 sync --only-show-errors "$gsrc/" "$GFSDIR/"
  ls "$GFSDIR" | wc -l; ls "$SEEDDIR" 2>/dev/null || true
  tl "stage done"
}

seed_prep() { # <seed grib2> <out>: the land-state records only, skin T blanked over water
  local in=$1 out=$2 d; d=$(dirname "$out")
  # instantaneous WEASD only (the file also carries an accumulated-snowfall WEASD record); LAND first
  # so the rpn register holds it when TMP:surface is processed
  wgrib2 "$in" -match ":LAND:surface:" -grib $d/land.g2 > /dev/null
  wgrib2 "$in" -match ":(TSOIL|SOILW):(0-0.1|0.1-0.4|0.4-1|1-2) m below ground:|:(WEASD|CNWAT):surface:(anl|[0-9]+ hour fcst):|:TMP:surface:" -grib $d/rest.g2 > /dev/null
  cat $d/land.g2 $d/rest.g2 | wgrib2 - -if ":LAND:" -rpn sto_1 -fi -if ":TMP:surface:" -rpn "rcl_1:mask" -fi -set_grib_type c3 -grib_out "$out" > /dev/null
  rm -f $d/land.g2 $d/rest.g2
  wgrib2 -s "$out"
}

stage_seed() { # the soil seed: one serial ungrib of the prepared seed file with its own Vtable and prefix
  local seed; seed=$(seed_file)
  if [ -z "$seed" ]; then log "no soil seed: the Noah state comes from the GFS"; return 0; fi
  log "ungrib soil seed $seed -> SEED:$(wpsdate $START)"
  mkdir -p ungrib/out ungrib/seed; ( cd ungrib/seed; rm -f SEED:* FILE:* GRIBFILE.*
    seed_prep "$seed" $PWD/seed.grib2 > seed.inv
    cp $HERE/parm/Vtable.SEED Vtable
    mk_nps $PARM/nam_namelist.nps_bocos $START $START
    sed -i "s/^ out_format = 'WPS'/ out_format = 'WPS',\n prefix = 'SEED'/" namelist.nps
    ln -sf $PWD/seed.grib2 GRIBFILE.AAA
    $EXEC/ungribs.exe > ungrib.out 2>&1 || { echo "ungrib seed failed"; tail ungrib.out; exit 1; }
    [ -s SEED:$(wpsdate $START) ] || { echo "no SEED intermediate file"; tail -20 ungrib.out; exit 1; }
    mv SEED:$(wpsdate $START) ../out/ )
}

stage_ungrib() { # one serial ungrib per GFS file, all in parallel (ops: 7 streams of 5 files)
  log "ungrib GFS $START f00..f$FHMAX"
  tl "ungrib start"
  mkdir -p ungrib/out
  one() {
    local fh=$1 v; v=$(ndate +$fh $START)
    mkdir -p ungrib/f$fh; cd ungrib/f$fh; rm -f FILE:* GRIBFILE.*
    cp $PARM/nam_Vtable.GFS.bocos Vtable
    mk_nps $PARM/nam_namelist.nps_bocos $v $v
    ln -sf $GFSDIR/gfs.t${pcyc}z.pgrb2.0p25.f0$fh GRIBFILE.AAA     # ops: pgrb2.0p25 only (getges pg2cur)
    $EXEC/ungribs.exe > ungrib.out 2>&1 || { echo "ungrib f$fh failed"; tail ungrib.out; return 1; }
    mv FILE:$(wpsdate $v) ../out/
  }
  export -f one ndate wpsdate mk_nps; export START PARM GFSDIR EXEC pcyc RUNDIR
  fhrs | xargs -P ${NPS_PARALLEL:-16} -I{} bash -c 'cd $RUNDIR && one {}'
  ls ungrib/out | wc -l
  stage_seed
  tl "ungrib done"
}

stage_metgrid() {
  local seedfile=ungrib/out/SEED:$(wpsdate $START)
  log "metgrid IC (nam_METGRID.TBL.NMM_gfsgrib2, dmpar, $NPS_NP tasks)"
  tl "metgrid start"
  mkdir -p metgrid_ic; ( cd metgrid_ic; rm -f met_nmb* FILE:* SEED:*
    mk_nps $PARM/nam_namelist.nps $START $START
    cp $PARM/nam_METGRID.TBL.NMM_gfsgrib2 METGRID.TBL
    cp $FIX/nam_geo_nmb.d01.dio geo_nmb.d01.dio
    ln -sf ../ungrib/out/FILE:$(wpsdate $START) .
    if [ -s ../$seedfile ]; then
      # NPS metgrid processes fg_name sources in order and a later source overwrites, point by point,
      # wherever it has valid data (docs/tm06-design.md): the seed goes LAST and wins inside grid 218.
      ln -sf ../$seedfile .
      sed -i "s/^ fg_name = 'FILE'/ fg_name = 'FILE','SEED'/" namelist.nps
      cat $HERE/parm/METGRID.TBL.seed >> METGRID.TBL
      log "  fg_name = 'FILE','SEED' (soil seed merged after the GFS)"
    fi
    $(mpi_cmd $NPS_NP core) $EXEC/metgrid.exe > metgrid.out 2>&1
    ls met_nmb.d01.*.dio )
  [ "${IC_ONLY:-0}" = 1 ] && return 0
  log "metgrid bocos (nam.METGRID.TBL.bocos, serial, 2 times per stream as ops)"
  mkdir -p metgrid_bc/out
  onem() {
    local s=$1 e=$2 h; mkdir -p metgrid_bc/s$s; cd metgrid_bc/s$s; rm -f met_nmb* FILE:*
    mk_nps $PARM/nam_namelist.nps_bocos $(ndate +$s $START) $(ndate +$e $START)
    cp $PARM/nam.METGRID.TBL.bocos METGRID.TBL
    cp $FIX/nam_geo_nmb.d01.dio geo_nmb.d01.dio
    for h in $(seq $s 3 $e); do ln -sf ../../ungrib/out/FILE:$(wpsdate $(ndate +$h $START)) .; done
    $EXEC/metgrid_serial.exe > metgrid.out 2>&1 || { tail metgrid.out; return 1; }
    mv met_nmb.d01.*.dio ../out/
  }
  export -f onem ndate wpsdate mk_nps; export START PARM FIX EXEC RUNDIR
  for s in $(seq 0 6 $FHMAX); do e=$((s + 3)); [ $e -gt $FHMAX ] && e=$FHMAX; echo "$s $e"; done \
    | xargs -P 16 -L1 bash -c 'cd $RUNDIR && onem $0 $1'
  ls metgrid_bc/out | wc -l
  [ "${NPS_CLEAN:-0}" = 1 ] && { rm -rf ungrib/f??; find ungrib/out -name "FILE:*" ! -name "FILE:$(wpsdate $START)" -delete; }   # keep the IC time for a re-run of the IC
  tl "metgrid done"
}

stage_nemsinterp() {
  log "nemsinterp IC"
  tl "nemsinterp start"
  mkdir -p nemsinterp_ic; ( cd nemsinterp_ic; rm -f input_domain_01* boco.*
    cp ../metgrid_ic/namelist.nps .
    ln -sf ../metgrid_ic/met_nmb.d01.*.dio .
    $(mpi_cmd $NPS_NP core) $EXEC/nemsinterp.exe > nemsinterp.out 2>&1
    ls -l input_domain_01_nemsio
    grep -A0 "min,max for TSK\|min,max for SMC\|min,max for STC\|min,max for SNO" nemsinterp.out | head -12 )
  [ "${IC_ONLY:-0}" = 1 ] && return 0
  log "nemsinterp bocos: 12 h streams of 5 met files (exnam_nemsinterp_boco1-7)"
  mkdir -p bocos
  onen() {
    local s=$1 e h; e=$((s + 12)); [ $e -gt $FHMAX ] && e=$FHMAX
    mkdir -p nemsinterp_bc/s$s; cd nemsinterp_bc/s$s; rm -f boco.* input_domain* met_nmb*
    mk_nps $PARM/nam_namelist.nps_bocos $(ndate +$s $START) $(ndate +$e $START)
    for h in $(seq $s 3 $e); do ln -sf ../../metgrid_bc/out/met_nmb.d01.$(wpsdate $(ndate +$h $START)):00:00.dio .; done
    $(mpi_cmd 4 none) $EXEC/nemsinterp.exe > nemsinterp.out 2>&1 || { tail nemsinterp.out; return 1; }   # 8 streams share the node: no pinning
    for b in boco.*; do mv $b ../../bocos/$(printf 'boco.%04d' $((10#${b#boco.} + s))); done
  }
  export -f onen ndate wpsdate mk_nps mpi_cmd; export START PARM EXEC RUNDIR FHMAX MPI
  seq 0 12 $((FHMAX - 1)) | xargs -P 8 -I{} bash -c 'cd $RUNDIR && onen {}'
  ls bocos
  [ "${NPS_CLEAN:-0}" = 1 ] && rm -rf metgrid_bc nemsinterp_bc
  tl "nemsinterp done"
}

stage_fcst() {
  local nt=$((INPES * JNPES + WRITE_GROUPS * WRITE_TASKS)) y=${START:0:4}
  log "fcst ${FHMAX} h from $START: ${INPES}x${JNPES} compute + ${WRITE_GROUPS}x${WRITE_TASKS} write = $nt tasks, filter_method $FILTER, precip bucket $PCPBUCKET h"
  tl "fcst start"
  mkdir -p fcst; cd fcst
  local restart=false rst00=${RST00:-true}   # RST00=false: no f00 restart file (restarts off)
  last=$(ls nmmb_rst_01_nio_*h_00m_00.00s 2>/dev/null | sort | tail -1 || true)
  if [ -n "${last:-}" ] && [ "${RESUME:-1}" = 1 ]; then   # Spot recovery (exnam_fcst RESTARTNZF)
    log "restarting from $last"; mv -f "$last" restart_file_01_nemsio; restart=true; rst00=false; FILTER=0
  fi
  local e; e=$(ndate +$FHMAX $START)
  # buckets: precip PCPBUCKET h (ops 00Z: 12; tm06: 3 so any product-clock window can be rebuilt),
  # heat/cloud/rad/evap 6 h as ops (a 6 h bucket on the START clock is also aligned on the C clock)
  sed -e "s:YSTART:${y}:" -e "s:MSTART:${START:4:2}:" -e "s:DSTART:${START:6:2}:" -e "s:HSTART:${pcyc}:" \
      -e "s:YEND:${e:0:4}:" -e "s:MEND:${e:4:2}:" -e "s:DEND:${e:6:2}:" -e "s:HEND:${e:8:2}:" \
      -e "s:INPES:$INPES:" -e "s:JNPES:$JNPES:" -e "s:WRITE_GROUPS:$WRITE_GROUPS:" -e "s:WRITE_TASKS:$WRITE_TASKS:" \
      -e "s:LENGTH:$FHMAX:" -e "s:RESINT:$RESTMIN:" -e "s:REST\b:$restart:" -e "s:FREE:true:" -e "s:OUTRST:$rst00:" \
      -e "s:WRTLAST:${WRTLAST:-true}:" -e "s:PFLAG:false:" -e "s:FILTEROPTION:$FILTER:" -e "s:USE_RADAR:0:" \
      -e "s:NUMDOM:1:" -e "s:NCHILD:0:" \
      -e "s:PRECIPBUCKET:$PCPBUCKET:" -e "s:HEATBUCKET:6:" -e "s:CLOUDBUCKET:6:" \
      -e "s:LWBUCKET:6:" -e "s:SWBUCKET:6:" -e "s:EVAPBUCKET:6:" \
      -e "s:^minutes_history\: *60:minutes_history\: $HISTMIN:" \
      $PARM/nam_configfile > configure_file_01
  grep -qE "INPES|JNPES|YSTART|FILTEROPTION|REST |NUMDOM" configure_file_01 && { echo "unsubstituted placeholder"; exit 1; }
  cp configure_file_01 model_configure
  [ $restart = true ] || ln -sf ../nemsinterp_ic/input_domain_01_nemsio input_domain_01_nemsio
  for b in ../bocos/boco.*; do ln -sf $b .; done
  ln -sf $FIX/nam_GWD.bin GWD_bin_01
  cp $FIX/nam_micro_lookup.dat ETAMPNEW_DATA.expanded_rain
  for t in GENPARM LANDUSE SOILPARM VEGPARM; do cp $FIX/nam_$t.TBL $t.TBL; done
  cp $PARM/nam_atmos.configure_nmm atmos.configure
  cp $PARM/nam_ocean.configure ocean.configure
  cp $PARM/nam_solver_state.txt solver_state.txt
  cp $PARM/nam_filt_vars_norad.txt filt_vars.txt
  cp $PARM/nam_nests.txt nests.txt
  cp $PARM/nam_climaeropac_global.txt aerosol.dat
  cp $FIX/nam_co2historicaldata_${y}.txt co2historicaldata_${y}.txt
  cp $FIX/nam_co2historicaldata_$((y - 1)).txt co2historicaldata_$((y - 1)).txt
  ln -sf $FIX/nam_global_o3prdlos.f77 fort.28
  ln -sf $FIX/nam_global_o3clim.txt fort.48
  export LANG=en_US
  [ -n "${FCST_CPUS:-}" ] && export I_MPI_PIN_PROCESSOR_LIST=$FCST_CPUS   # keep clear of concurrent UPP
  # UPP/products run alongside on the write ranks' cores (runner.sh POST_CPUS): let idle MPI
  # ranks yield instead of spinning so those cores are usable (OpenMPI only)
  [ "${FCST_YIELD:-0}" = 1 ] && export OMPI_MCA_mpi_yield_when_idle=1
  local exe=${NEMS_EXE:-$EXEC/NEMS.x}
  /usr/bin/time -v $(mpi_cmd $nt core "${FCST_CPUS:-}") $exe > nems.out 2> nems.err
  log "$(basename $exe) exit $?"
  tl "fcst done"
}

post_fhrs() { seq -f %02g $FH0 3 "$FHMAX"; }   # integration hours UPP processes (tm06: 6..90)

stage_post() { # UPP per history file; GRIB2 outputs BGDAWP/BGRDSF/BGRD3D as exnam_post.sh; then products
  log "post with $NPOST tasks${POST_CPUS:+ on cpus $POST_CPUS}"
  tl "post start"
  mkdir -p post grib2
  local fh v
  for fh in ${POST_FHRS:-$(post_fhrs)}; do
    local h=fcst/nmmb_hst_01_nio_00${fh}h_00m_00.00s
    if [ -s grib2/nam.t${pcyc}z.bgdawp${fh}.tm00.grib2 ]; then
      [ "${PRODUCTS:-1}" = 1 ] && $HERE/products.sh $fh >> products.log 2>&1
      continue
    fi
    while [ ! -s fcst/fcstdone.01.00${fh}h_00m_00.00s ]; do
      [ "${WAIT:-0}" = 1 ] || { echo "no $h"; return 1; }
      pgrep -x NEMS.x > /dev/null || { sleep 60; [ -s fcst/fcstdone.01.00${fh}h_00m_00.00s ] && break; echo "NEMS.x not running and no f$fh"; return 1; }
      sleep 30; done
    v=$(ndate +$fh $START)
    ( cd post; rm -f BG* itag
      cp $PARM/nam_post_avblflds.xml post_avblflds.xml
      cp $PARM/nam_params_grib2_tbl params_grib2_tbl_new
      cp $FIX/nam_micro_lookup.dat eta_micro_lookup.dat
      # the analysis control (_00h, no accumulations) only for a true analysis; the tm06 f00 is
      # integration hour 6 and uses the forecast control (products.sh relabels it)
      if [ $fh = 00 ]; then cp $PARM/nam_cntrl_cmaq_flatfile.txt_00h postxconfig-NT.txt
      else cp $PARM/nam_cntrl_cmaq_flatfile.txt postxconfig-NT.txt; fi
      printf '%s\n' "$RUNDIR/$h" binarynemsio grib2 "${v:0:4}-${v:4:2}-${v:6:2}_${v:8:2}:00:00" NMM > itag
      local t0=$SECONDS
      [ -n "${POST_CPUS:-}" ] && export I_MPI_PIN_PROCESSOR_LIST=$POST_CPUS
      $(mpi_cmd $NPOST core "${POST_CPUS:-}") $EXEC/ncep_post < itag > post_f$fh.out 2>&1
      for k in BGDAWP BGRDSF BGRD3D; do
        [ -s $k.GrbF$fh ] && mv $k.GrbF$fh ../grib2/nam.t${pcyc}z.$(echo $k | tr A-Z a-z)${fh}.tm00.grib2
      done
      echo "post f$fh $((SECONDS - t0)) s" | tee -a ../post_times.txt ) || true   # the check below reports; set -e would end the function silently here
    [ -s grib2/nam.t${pcyc}z.bgdawp${fh}.tm00.grib2 ] || { echo "UPP f$fh produced no BGDAWP"; tail -30 post/post_f$fh.out; return 1; }
    tl "post f$fh done"
    if [ "${PRODUCTS:-1}" = 1 ]; then   # both modes (anl: no clock shift, FH0=0)
      $HERE/products.sh $fh >> products.log 2>&1 || { echo "products f$fh failed"; tail -20 products.log; return 1; }
    fi
  done
  tl "post done"
}

stage_products() { local fh; for fh in ${POST_FHRS:-$(post_fhrs)}; do $HERE/products.sh $fh; done; }

stage_sync() {
  aws s3 sync --only-show-errors grib2 $S3RUN/grib2/ --exclude "*" --include "*bgdawp*"
  aws s3 sync --only-show-errors grib2 $S3RUN/grib2-all/
  [ "${SYNC_HISTORY:-1}" = 1 ] && aws s3 sync --only-show-errors fcst $S3RUN/history/ --exclude "*" --include "nmmb_hst_*" --include "nmmb_rst_*" --include "*.ctl"
  aws s3 cp --only-show-errors --recursive . $S3RUN/logs/ --exclude "*" --include "*.out" --include "*.err" \
    --include "*/configure_file_01" --include "post_times.txt" --include "*.log" --include "timeline.txt" --include "*.inv" --include "*/namelist.nps"
}

[ $# -gt 0 ] || { sed -n 2,22p "$0"; exit 1; }
for s in "$@"; do
  case $s in
    nps) for t in ungrib metgrid nemsinterp; do t0=$SECONDS; stage_$t; log "$t done in $((SECONDS-t0)) s"; done ;;
    all) for t in stage ungrib metgrid nemsinterp fcst post; do t0=$SECONDS; stage_$t; log "$t done in $((SECONDS-t0)) s"; done ;;
    *) t0=$SECONDS; ( stage_$s ); log "$s done in $((SECONDS-t0)) s" ;;
  esac
done
