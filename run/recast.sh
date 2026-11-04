#!/bin/bash
# NAM 12 km parent-domain cold-start recast: GFS -> NPS -> NEMS.x (NMMB) -> UPP.
# Follows exnam_coldstart_prep.sh, exnam_{ungrib,metgrid}_boco.sh, exnam_nemsinterp_boco*.sh,
# exnam_fcst.sh and exnam_post.sh with plain paths and Intel MPI or OpenMPI; see run/README.md.
#
# usage: recast.sh <stage...>   stages: ungrib metgrid nemsinterp fcst post sync  (or: nps, all)
# env:   CYCLE=2026110100 FHMAX=84 INPES=4 JNPES=7 WRITE_GROUPS=1 WRITE_TASKS=4 NPOST=8
#        RUNDIR=/opt/nam/runs/$CYCLE  S3RUN=s3://.../cases/$CYCLE/recast  FILTER=3
#        RESTMIN=720 RST00=true WRTLAST=true (restarts; RESTMIN=100800 RST00=false WRTLAST=false = none;
#        RESTMIN*60 must be a multiple of the 25 s timestep)  SYNC_HISTORY=1
#        NEMS_EXE=/opt/nam/work/exec/NEMS.x (NEMS_debug.x for the trap build)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)

CYCLE=${CYCLE:-2026110100}
FHMAX=${FHMAX:-84}
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
GFSDIR=${GFSDIR:-/opt/nam/cases/$CYCLE/gfs}
RUNDIR=${RUNDIR:-/opt/nam/runs/$CYCLE}
S3RUN=${S3RUN:-s3://nam-recast-617711905691/cases/$CYCLE/recast}
cyc=${CYCLE:8:2}

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
  # UPP writes GRIB2 with MPI-IO; OpenMPI's default OMPIO component dies with SIGBUS on rank 0
  # (aarch64, 4.1.6) and ROMIO works, so exclude OMPIO (the name-independent form of io=romio321).
  export OMPI_MCA_io=${OMPI_MCA_io:-^ompio}
fi
export MPI
ulimit -s unlimited || true
# mpi_cmd <ntasks> <core|none> [cpu list]: the mpirun prefix. Intel MPI pins through
# I_MPI_PIN_DOMAIN/I_MPI_PIN_PROCESSOR_LIST (exported by the callers, as in Phase 0); OpenMPI
# needs explicit --bind-to core (its default for >2 ranks is socket) and --cpu-set for a subset.
mpi_cmd() {
  local n=$1 bind=$2 cpus=${3:-}
  if [ "$MPI" = intel ]; then echo "mpirun -n $n -ppn $n"
  elif [ -n "$cpus" ]; then echo "mpirun -n $n --cpu-set $cpus --bind-to core --map-by core"
  elif [ "$bind" = core ]; then echo "mpirun -n $n --bind-to core --map-by core"
  else echo "mpirun -n $n --bind-to none"; fi
}

ndate() { date -u -d "${2:0:8} ${2:8:2}:00 UTC $1 hours" +%Y%m%d%H; }   # ndate <+-h> <yyyymmddhh>
wpsdate() { echo "${1:0:4}-${1:4:2}-${1:6:2}_${1:8:2}"; }
log() { echo "[$(date -u +%T)] $*"; }
mkdir -p "$RUNDIR"; cd "$RUNDIR"
fhrs() { seq -f %02g 0 3 "$FHMAX"; }

# namelist.nps from a template with YSTART..HEND replaced (exnam_* sed chains)
mk_nps() { # mk_nps <template> <start yyyymmddhh> <end yyyymmddhh>
  local s=$2 e=$3
  sed -e "s:YSTART:${s:0:4}:" -e "s:MSTART:${s:4:2}:" -e "s:DSTART:${s:6:2}:" -e "s:HSTART:${s:8:2}:" \
      -e "s:YEND:${e:0:4}:" -e "s:MEND:${e:4:2}:" -e "s:DEND:${e:6:2}:" -e "s:HEND:${e:8:2}:g" \
      -e "s:IGNORE_GRIDGEN:.false.:" "$1" > namelist.nps
}

stage_ungrib() { # one serial ungrib per GFS file, all in parallel (ops: 7 streams of 5 files)
  log "ungrib f00..f$FHMAX"
  mkdir -p ungrib/out
  one() {
    local fh=$1 v; v=$(ndate +$fh $CYCLE)
    mkdir -p ungrib/f$fh; cd ungrib/f$fh; rm -f FILE:* GRIBFILE.*
    cp $PARM/nam_Vtable.GFS.bocos Vtable
    mk_nps $PARM/nam_namelist.nps_bocos $v $v
    ln -sf $GFSDIR/gfs.t${cyc}z.pgrb2.0p25.f0$fh GRIBFILE.AAA     # ops: pgrb2.0p25 only (getges pg2cur)
    $EXEC/ungribs.exe > ungrib.out 2>&1 || { echo "ungrib f$fh failed"; tail ungrib.out; return 1; }
    mv FILE:$(wpsdate $v) ../out/
  }
  export -f one ndate wpsdate mk_nps; export CYCLE PARM GFSDIR EXEC cyc RUNDIR
  fhrs | xargs -P ${NPS_PARALLEL:-16} -I{} bash -c 'cd $RUNDIR && one {}'
  ls ungrib/out | wc -l
}

stage_metgrid() {
  log "metgrid IC (nam_METGRID.TBL.NMM_gfsgrib2, dmpar, $NPS_NP tasks)"
  mkdir -p metgrid_ic; ( cd metgrid_ic; rm -f met_nmb*
    mk_nps $PARM/nam_namelist.nps $CYCLE $CYCLE
    cp $PARM/nam_METGRID.TBL.NMM_gfsgrib2 METGRID.TBL
    cp $FIX/nam_geo_nmb.d01.dio geo_nmb.d01.dio
    ln -sf ../ungrib/out/FILE:$(wpsdate $CYCLE) .
    $(mpi_cmd $NPS_NP core) $EXEC/metgrid.exe > metgrid.out 2>&1
    ls met_nmb.d01.*.dio )
  log "metgrid bocos (nam.METGRID.TBL.bocos, serial, 2 times per stream as ops)"
  mkdir -p metgrid_bc/out
  onem() {
    local s=$1 e=$2 h; mkdir -p metgrid_bc/s$s; cd metgrid_bc/s$s; rm -f met_nmb* FILE:*
    mk_nps $PARM/nam_namelist.nps_bocos $(ndate +$s $CYCLE) $(ndate +$e $CYCLE)
    cp $PARM/nam.METGRID.TBL.bocos METGRID.TBL
    cp $FIX/nam_geo_nmb.d01.dio geo_nmb.d01.dio
    for h in $(seq $s 3 $e); do ln -sf ../../ungrib/out/FILE:$(wpsdate $(ndate +$h $CYCLE)) .; done
    $EXEC/metgrid_serial.exe > metgrid.out 2>&1 || { tail metgrid.out; return 1; }
    mv met_nmb.d01.*.dio ../out/
  }
  export -f onem ndate wpsdate mk_nps; export CYCLE PARM FIX EXEC RUNDIR
  for s in $(seq 0 6 $FHMAX); do e=$((s + 3)); [ $e -gt $FHMAX ] && e=$FHMAX; echo "$s $e"; done \
    | xargs -P 16 -L1 bash -c 'cd $RUNDIR && onem $0 $1'
  ls metgrid_bc/out | wc -l
}

stage_nemsinterp() {
  log "nemsinterp IC"
  mkdir -p nemsinterp_ic; ( cd nemsinterp_ic; rm -f input_domain_01* boco.*
    cp ../metgrid_ic/namelist.nps .
    ln -sf ../metgrid_ic/met_nmb.d01.*.dio .
    $(mpi_cmd $NPS_NP core) $EXEC/nemsinterp.exe > nemsinterp.out 2>&1
    ls -l input_domain_01_nemsio )
  log "nemsinterp bocos: 12 h streams of 5 met files (exnam_nemsinterp_boco1-7)"
  mkdir -p bocos
  onen() {
    local s=$1 e h; e=$((s + 12)); [ $e -gt $FHMAX ] && e=$FHMAX
    mkdir -p nemsinterp_bc/s$s; cd nemsinterp_bc/s$s; rm -f boco.* input_domain* met_nmb*
    mk_nps $PARM/nam_namelist.nps_bocos $(ndate +$s $CYCLE) $(ndate +$e $CYCLE)
    for h in $(seq $s 3 $e); do ln -sf ../../metgrid_bc/out/met_nmb.d01.$(wpsdate $(ndate +$h $CYCLE)):00:00.dio .; done
    $(mpi_cmd 4 none) $EXEC/nemsinterp.exe > nemsinterp.out 2>&1 || { tail nemsinterp.out; return 1; }   # 8 streams share the node: no pinning
    for b in boco.*; do mv $b ../../bocos/$(printf 'boco.%04d' $((10#${b#boco.} + s))); done
  }
  export -f onen ndate wpsdate mk_nps mpi_cmd; export CYCLE PARM EXEC RUNDIR FHMAX MPI
  seq 0 12 $((FHMAX - 1)) | xargs -P 8 -I{} bash -c 'cd $RUNDIR && onen {}'
  ls bocos
}

stage_fcst() {
  local nt=$((INPES * JNPES + WRITE_GROUPS * WRITE_TASKS)) y=${CYCLE:0:4}
  log "fcst ${FHMAX} h: ${INPES}x${JNPES} compute + ${WRITE_GROUPS}x${WRITE_TASKS} write = $nt tasks, filter_method $FILTER"
  mkdir -p fcst; cd fcst
  local restart=false rst00=${RST00:-true}   # RST00=false: no f00 restart file (restarts off)
  last=$(ls nmmb_rst_01_nio_*h_00m_00.00s 2>/dev/null | sort | tail -1 || true)
  if [ -n "${last:-}" ] && [ "${RESUME:-1}" = 1 ]; then   # Spot recovery (exnam_fcst RESTARTNZF)
    log "restarting from $last"; mv -f "$last" restart_file_01_nemsio; restart=true; rst00=false; FILTER=0
  fi
  local e; e=$(ndate +$FHMAX $CYCLE)
  # 00Z buckets as ops (pcp 12 h, heat/cloud/rad/evap 6 h)
  sed -e "s:YSTART:${y}:" -e "s:MSTART:${CYCLE:4:2}:" -e "s:DSTART:${CYCLE:6:2}:" -e "s:HSTART:${cyc}:" \
      -e "s:YEND:${e:0:4}:" -e "s:MEND:${e:4:2}:" -e "s:DEND:${e:6:2}:" -e "s:HEND:${e:8:2}:" \
      -e "s:INPES:$INPES:" -e "s:JNPES:$JNPES:" -e "s:WRITE_GROUPS:$WRITE_GROUPS:" -e "s:WRITE_TASKS:$WRITE_TASKS:" \
      -e "s:LENGTH:$FHMAX:" -e "s:RESINT:$RESTMIN:" -e "s:REST\b:$restart:" -e "s:FREE:true:" -e "s:OUTRST:$rst00:" \
      -e "s:WRTLAST:${WRTLAST:-true}:" -e "s:PFLAG:false:" -e "s:FILTEROPTION:$FILTER:" -e "s:USE_RADAR:0:" \
      -e "s:NUMDOM:1:" -e "s:NCHILD:0:" \
      -e "s:PRECIPBUCKET:${PCPBUCKET:-12}:" -e "s:HEATBUCKET:6:" -e "s:CLOUDBUCKET:6:" \
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
  local exe=${NEMS_EXE:-$EXEC/NEMS.x}
  /usr/bin/time -v $(mpi_cmd $nt core "${FCST_CPUS:-}") $exe > nems.out 2> nems.err
  log "$(basename $exe) exit $?"
}

stage_post() { # UPP per history file; GRIB2 outputs BGDAWP/BGRDSF/BGRD3D as exnam_post.sh
  log "post with $NPOST tasks"
  mkdir -p post grib2
  local fh v
  for fh in ${POST_FHRS:-$(fhrs)}; do
    local h=fcst/nmmb_hst_01_nio_00${fh}h_00m_00.00s
    [ -s grib2/nam.t${cyc}z.bgdawp${fh}.tm00.grib2 ] && continue
    while [ ! -s fcst/fcstdone.01.00${fh}h_00m_00.00s ]; do
      [ "${WAIT:-0}" = 1 ] || { echo "no $h"; return 1; }
      pgrep -x NEMS.x > /dev/null || { sleep 60; [ -s fcst/fcstdone.01.00${fh}h_00m_00.00s ] && break; echo "NEMS.x not running and no f$fh"; return 1; }
      sleep 30; done
    v=$(ndate +$fh $CYCLE)
    ( cd post; rm -f BG* itag
      cp $PARM/nam_post_avblflds.xml post_avblflds.xml
      cp $PARM/nam_params_grib2_tbl params_grib2_tbl_new
      cp $FIX/nam_micro_lookup.dat eta_micro_lookup.dat
      if [ $fh = 00 ]; then cp $PARM/nam_cntrl_cmaq_flatfile.txt_00h postxconfig-NT.txt
      else cp $PARM/nam_cntrl_cmaq_flatfile.txt postxconfig-NT.txt; fi
      printf '%s\n' "$RUNDIR/$h" binarynemsio grib2 "${v:0:4}-${v:4:2}-${v:6:2}_${v:8:2}:00:00" NMM > itag
      local t0=$SECONDS
      [ -n "${POST_CPUS:-}" ] && export I_MPI_PIN_PROCESSOR_LIST=$POST_CPUS
      $(mpi_cmd $NPOST core "${POST_CPUS:-}") $EXEC/ncep_post < itag > post_f$fh.out 2>&1
      for k in BGDAWP BGRDSF BGRD3D; do
        [ -s $k.GrbF$fh ] && mv $k.GrbF$fh ../grib2/nam.t${cyc}z.$(echo $k | tr A-Z a-z)${fh}.tm00.grib2
      done
      echo "post f$fh $((SECONDS - t0)) s" | tee -a ../post_times.txt )
    [ -s grib2/nam.t${cyc}z.bgdawp${fh}.tm00.grib2 ] || { echo "UPP f$fh produced no BGDAWP"; tail -30 post/post_f$fh.out; return 1; }
  done
}

stage_sync() {
  aws s3 sync --only-show-errors grib2 $S3RUN/grib2/ --exclude "*" --include "*bgdawp*"
  aws s3 sync --only-show-errors grib2 $S3RUN/grib2-all/
  [ "${SYNC_HISTORY:-1}" = 1 ] && aws s3 sync --only-show-errors fcst $S3RUN/history/ --exclude "*" --include "nmmb_hst_*" --include "nmmb_rst_*" --include "*.ctl"
  aws s3 cp --only-show-errors --recursive . $S3RUN/logs/ --exclude "*" --include "*.out" --include "*.err" \
    --include "*/configure_file_01" --include "post_times.txt" --include "*.log"
}

[ $# -gt 0 ] || { sed -n 2,9p "$0"; exit 1; }
for s in "$@"; do
  case $s in
    nps) for t in ungrib metgrid nemsinterp; do t0=$SECONDS; stage_$t; log "$t done in $((SECONDS-t0)) s"; done ;;
    all) for t in ungrib metgrid nemsinterp fcst post; do t0=$SECONDS; stage_$t; log "$t done in $((SECONDS-t0)) s"; done ;;
    *) t0=$SECONDS; ( stage_$s ); log "$s done in $((SECONDS-t0)) s" ;;
  esac
done
