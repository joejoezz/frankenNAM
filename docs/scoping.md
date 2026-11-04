# Scoping: a community/private 12 km NAM "recast"

Researched 3 Nov 2026. Sources checked: the NCO code tree, the NWS retirement notices (SCN 26-47/26-48), the NAM v4 release notes, the operational Rocoto XML and node-decomposition files, NOMADS and AWS Open Data listings, GSI source tree, current us-west-2 Spot prices.

## Context

NCEP retired the NAM (12 km parent + 3 km nests), SREF, HREF, HiresW and NAM MOS on 3 Nov 2026 12Z, replaced by RRFS/REFS. Forecasters want the 12 km NAM back, mainly for its winter-storm behaviour (BMJ/Ferrier physics, cold-air damming, p-type, soundings/BUFKIT). Joe asks: is a private re-run possible, what would it cost, and what are the hurdles, with data assimilation suspected as the hardest part. The paleo-planet project already runs MPAS on AWS Spot, so compiled-NWP-on-cloud is a known pattern.

Short answers:

1. **Possible?** Yes for a cold-start "recast" (NAM dynamics + physics initialised from GFS/GDAS, GFS lateral boundaries). The complete production tree is online today: model, preprocessor, GSI, post, fix files, scripts. **Not possible** to reproduce the operational analysis faithfully: the 80-member GDAS ensemble it needs is not published. A reduced 3DVar is feasible but is a second project.
2. **Cost?** Compute is cheap: roughly $10-30 per 84 h forecast on Spot, so $1-4k/month for four cycles a day. Distribution egress can match that. The real cost is engineering time: ~3-6 weeks to a validated recast, months more for any DA.
3. **Hurdles, ranked:** (a) the source disappears from NCO's site "upon retirement" and is then by-request only, so mirror it now; (b) porting a 2017-era NEMS/ESMF 7.1 build off WCOSS2 (Intel 19 classic ifort, Cray MPICH, nemsio); (c) rewriting the WCOSS2-bound workflow (ecflow/PBS/module paths); (d) wall-clock vs Spot (single-node 192-core box ≈ 3-4 h per run); (e) DA: no public ensemble, NAM obs stream ends, RAP stream also sunsets eventually; (f) egress cost and the question of who the users are.

## What is actually online (verified 3 Nov 2026)

`https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/nam.v4.2.14/` contains:

- `sorc/`: `nam_nems_nmmb.fd` (NEMS + NMMB core, AppBuilder), `nam_nps.fd` (NPS: geogrid/ungrib/metgrid/nemsinterp), `nam_gsi.fd`, `nam_post0.fd` + `nam_nceppost.fd` (UPP), `nam_sndp.fd` (BUFR soundings), land utilities, precip tools, plus build logs from Feb 2022.
- `fix/`: full set including `geog/` (30 s terrain, 2 min landuse/soil, 1 km landcover), `nam_CRTM_Coefficients/`, GSI static background-error file `nam_nmmstat_na.gcv`, convinfo/satinfo, nest statics, CO2 files to 2026.
- `parm/`: `nam_configfile` (parent), nest configfiles, NPS namelists, post control files, node decompositions.
- `scripts/` (48 `exnam_*.sh`), `jobs/`, `ush/`, `ecf/`, `rocoto/` (incl. `NAM_wcoss2_coldstartNAM_off_GDAS.xml`, i.e. a cold-start-from-GDAS workflow already exists), `versions/build.ver`, `modulefiles/wcoss2/build/v4.0.0_build`.

SCN 26-47 (9 Sep 2026): "This software will be removed upon the retirement of these applications. After this date the software will only be available upon request." It is still up as of today. **Mirroring the whole tree is the first action regardless of anything else.** Expect a few GB (geog 30 s files are the bulk).

Licensing: US-government work, public domain; the notice says "as-is for community use", no support. Do not brand the output as NOAA's NAM; call it a recast.

Community release: DTC's NEMS-NMMB v1.0 (2016) is unsupported and its download pages now 404. The NCO tree is the only complete source.

## The system as it ran (from parm + rocoto)

| Item | Value |
|---|---|
| Parent grid | 954 × 835 × 60 levels, rotated lat-lon B-grid, centre 54N 106W, 12 km (North America, much bigger than CONUS) |
| Time step | 25⅓ s (`dt_int 25, dt_num 0, dt_den 3`) |
| Physics | Ferrier-Aligo hires microphysics, BMJ convection, MYJ PBL + surface layer, Noah LSM, RRTM SW/LW |
| Forecast | 84 h, 4 cycles/day; nests (3 km CONUS/AK, Hawaii, PR, fire wx) to 60 h |
| Ops decomposition, parent | 256 compute + 12 write tasks (×2 threads = ~512 cores) for 0-60 h alongside nests; 500+12 tasks for 60-84 h, ≤30 min wall on 4 WCOSS2 nodes (AMD Milan, 128 cores/node) |
| Whole package | 41 nodes × 63 tasks × 2 threads = 5,166 cores, 2:45 wall |
| DA (NDAS) | 6 h catch-up: GSI hybrid 3DEnVar every hour tm06→tm00 (parent 144 tasks × 8 threads, 30 min wall each) + six 1 h forecasts (parent 642 tasks); radar reflectivity via GSD cloud analysis + DFI temperature tendencies, lightning, radar radial winds, radiances (AMSU-A, MHS, HIRS4, ATMS, CrIS, SEVIRI, SSMIS, GOES), satwinds, GPSRO; land states cycled continuously |
| Build stack | Intel 19.1.3 classic ifort, Cray MPICH 8.1.9, ESMF 7.1.0r, netCDF 4.7.4/HDF5 1.10.6, nemsio 2.5.2, CRTM 2.3.0, bufr 11.5.0, g2 3.4.5, w3emc/w3nco/bacio/sp/ip/sigio/sfcio/gfsio/landsfcutil |

Compute estimate for the 12 km parent alone, 84 h: the 60-84 h parent-only job is ≤256 core-hours per 24 h; scaling gives **~600-900 Milan core-hours per 84 h run**. Treat 700 as the planning number until we measure.

## Inputs and their availability

| Need | Status |
|---|---|
| GFS/GDAS 0.25° GRIB2 for IC/LBC (NPS `Vtable.GFS`) | AWS `noaa-gfs-bdp-pds`, free in-region, ~0.5 GB per file, back to 2021 |
| Archived NAM output for validation | AWS `noaa-nam-pds`, 16 Sep 2021 → 3 Nov 2026 (full awphys/conusnest/bufrsnd); NOMADS keeps ~8 days |
| Obs: NAM hourly dump stream (`obsproc/prod/nam.*`) | ends with the model (last day 20261103) |
| Obs: RAP hourly stream (`obsproc/prod/rap.*`) | live: hourly `prepbufr.tm00.nr` (~11 MB), `nexrad` (~870 MB), `satwnd`, `1bamua`, `1bmhs`, `lgycld`. Continues until RAP/HRRR retire (later RRFS version, no date yet) |
| Obs: GDAS 6-hourly stream (`obsproc/prod/gdas.*`) | live, 35 BUFR types incl. ATMS, CrIS, IASI, GPSRO; `.nr` = restricted data removed |
| GDAS 80-member EnKF ensemble (hybrid EnVar) | **not public**: AWS and NOMADS `enkfgdas/.../memNNN/` carry only `sfcf*.nc`, no atmospheric files |
| Snow (IMS, 557 WW), RTG SST, Stage IV | IMS and SST public; 557 WW snow depth is not; substitutes exist (GFS snow, NSIDC) |
| GSI code support for NMMB | NOAA-EMC/GSI `develop` still ships `src/GSD/gsdcloud4nmmb`; the frozen `nam_gsi.fd` is in the tree anyway |

Obs dumps are **not** on AWS Open Data; only NOMADS (≈10-day retention), so any DA path needs a daily puller from day one.

## Recommended approach: prove the cheap recast first

Phase 0 and 1 deliberately exclude DA. A GFS-initialised NMMB with NAM physics gives the "NAM look" from ~12 h onward; the operational analysis mostly bought the first 6-12 h and the 3 km nest. Validation against the archived NAM makes that claim measurable instead of asserted.

### Phase 0: mirror + build + one run (2-3 weeks, <$100 compute)

1. `wget -r -np -nH` the whole `nam.v4.2.14/` tree to S3 (and `nam.v4.2.13/` if present, the notice lists that one). Also snapshot `versions/`, `docs/`, `parm/`, `rocoto/`. Do this this week.
2. Build in Docker on **x86 with Intel oneAPI 2024.x classic `ifort`** first (lowest porting risk; 2025 toolkits dropped ifort). Library stack via spack or hand-built: ESMF 7.1.0r (may need 8.x with small NEMS patches if 7.1 won't compile), netCDF 4.7/HDF5 1.10, NCEPLIBS at the pinned versions from `build.ver` (all on GitHub under NOAA-EMC). Targets in order: NPS → NMMB → UPP (`nam_post0`) → `nam_sndp`. Skip GSI, CMAQ, GOES-TB, firewx, nests.
3. Replace the WCOSS2 scripts with a thin driver (bash or Python) that reproduces `exnam_coldstart_prep` → NPS (geogrid once; ungrib/metgrid/nemsinterp per cycle) → `exnam_fcst` for domain 1 only, `filter_method 0`, `radar_init` off, no TC relocation → UPP to GRIB2 on grid 218 (the familiar 12 km awphys grid) → BUFR soundings.
4. Run one historical case on a single Spot node and compare visually with the archived NAM for the same cycle.

Decision gate: it compiles, runs 84 h stably, output resembles the archive. If NEMS/ESMF 7.1 refuses to build after ~1 week of effort, stop and report; that is the one hurdle that can kill the project outright.

### Phase 1: validate as a hindcast (1-2 weeks, $200-600 compute)

- 15-25 archived cycles spanning winter storms, Pacific NW orographic events, a cold-air-damming case, a summer convective case, using the GFS that was available then (AWS archive) as IC/LBC.
- Score recast vs archived NAM vs GFS vs observations: 500 hPa Z, 2 m T/Td, 10 m wind, 6 h QPF, p-type, snowfall at SNOTEL/ASOS. Pay attention to the first 12 h (spin-up, no mesoscale analysis) and to near-surface fields (land states not cycled).
- Cheap, big win: once daily runs start, **cycle the Noah land states** run-to-run with `exnam_sfcupdate`/`partialcyc` logic. That recovers most of what the NAM's land cycling gave and costs nothing.
- Try the Graviton/gfortran port here, using the x86 run as the reference. Known gfortran fixes went into NMMB in 2014; expect `-fallow-argument-mismatch`-class issues. If it works, compute cost roughly halves.

Decision gate: recast is closer to the archived NAM than the GFS is, at 12-84 h, on the fields people care about. Publish the scorecard; it is also the credibility document for the product.

### Phase 2: daily operations (2-4 weeks)

- 4 cycles/day, 12 km parent, 84 h, triggered when GFS f084 lands on AWS (~3.5 h after cycle time), so products land ~7-8 h after cycle time on a single node, ~5 h with 3-4 nodes. Products: GRIB2 on grid 218, BUFKIT/BUFR soundings, a handful of maps. Checkpoint/restart (NMMB writes nemsio restarts) for Spot interruption, retry-then-on-demand as in PPS.
- Same AWS pattern as PPS/wsis: Batch or ECS task, S3 output, CloudFront, alarms, budget.

### DA, if ever (months; separate decision)

Options in increasing cost. The faithful option does not exist.

1. **Warm start from someone else's analysis**: initialise from RAP (13 km, hourly) or RRFS (3 km) analyses through NPS instead of GFS. Gets a mesoscale analysis for free, keeps the NAM forecast model. Likely the best value; costs a Vtable and a test. RAP is on borrowed time; RRFS is the long-term source.
2. **GSI 3DVar with static BE** (`nam_nmmstat_na.gcv` is in `fix/`), obs from the RAP hourly stream, optionally the GSD cloud analysis + DFI for radar. ~5× the compute of the free forecast if the full 6 h catch-up is kept (ops: ~3-5k core-hours per cycle for DA vs ~700 for the forecast). A 1-3 h catch-up would be cheaper and still useful.
3. **Hybrid EnVar**: requires an ensemble nobody publishes at the needed resolution. GEFS on AWS is GRIB2 only, not the native files GSI reads. Not viable without running our own ensemble. Rule it out.

## Cost estimate

Spot prices read today in us-west-2 (per hour): c7g.16xlarge $0.76-0.98 (64 Graviton3 cores), c8g.48xlarge $2.70-2.95 (192 Graviton4 cores), c7a.48xlarge $2.4-4.2 (96 Genoa cores), c7i.48xlarge ~$4.5 (96 cores). HPC instances with EFA (hpc7g, us-east-1 only; hpc7a) have no Spot, hpc7g.16xlarge ≈ $1.68/h on-demand.

| Item | Estimate |
|---|---|
| One 84 h run, x86 Spot (c7a.48xlarge, ~700 core-h) | $18-30, ~7 h wall on one node, ~3.5 h on two |
| One 84 h run, Graviton Spot (c8g.48xlarge) if the port works | $10-14, ~3.5-4 h wall on one node |
| One 84 h run, hpc7g on-demand, 8 nodes with EFA | ~$18, ~1.5 h wall |
| Daily ops, 4 cycles | $40-120/day → $1.2-3.6k/month compute |
| Input pull (GFS 0.25°, ~15 GB/cycle) | free in us-east-1, ~$0.30/cycle cross-region |
| Output storage (~5 GB GRIB2 per run, 30-day keep) | <$20/month |
| Distribution egress | the wildcard: 100 users × 5 GB/day ≈ 500 GB/day ≈ $1.3k/month at CloudFront rates; near zero if we serve maps + BUFKIT files only, or a requester-pays bucket for GRIB2 |
| Phase 0 + 1 compute | $300-700 total |
| Adding 3DVar DA | roughly 5× compute → $6-15k/month, plus months of work |
| Engineering | Phase 0-2 ≈ 5-9 weeks of focused work; DA option 2 ≈ 2-4 months more |

For comparison the MPAS 120 km 10-day global run was $0.54; this is ~20-50× more per run because the domain has ~50× the cells and a 30× smaller time step.

## Hurdles, ranked by likelihood of stopping the project

1. **Source availability** (certain, trivial to fix today, impossible later): mirror now.
2. **Build portability** (the real risk): 2017 NEMS with ESMF 7.1.0r, Intel 19 classic, Cray MPICH, nemsio I/O. Classic ifort still exists in oneAPI ≤2024.2; pin to it. ESMF 7.1.0r may not compile with current compilers; ESMF 8.x changed APIs NEMS touches. Budget one week; if it does not build, stop.
3. **Workflow port**: 48 ex-scripts assume WCOSS2 (`/lfs`, PBS, `mpiexec` with Cray PALS, ecflow, `module load`). Write a new ~500-line driver rather than porting them; use the scripts as the spec.
4. **Wall clock on Spot**: no EFA on Spot; single 192-core node gives ~3.5-4 h per run (Graviton) or ~7 h (x86 96-core). Acceptable for a day 1-3 product, not for nowcasting. Multi-node without EFA is probably fine for 2-4 nodes at this grid size; measure.
5. **Data assimilation**: faithful reproduction impossible (no ensemble); NAM obs stream gone; RAP obs stream will go later; restricted obs never available. The cold-start recast and the warm-start-from-RRFS option sidestep this.
6. **Scientific honesty**: a GFS-initialised NAM is not the NAM. The hindcast scorecard is how we say exactly what it is.
7. **Demand and egress**: who are the users and what format do they want. BUFKIT soundings and maps are cheap to serve; raw GRIB2 to many users is not.
8. **Graviton/gfortran port** (optional cost lever, not a blocker): NMMB had gfortran fixes in 2014 but has been Intel-only in ops since; expect a few days of argument-mismatch and BOZ fixes.

## Verification (end-to-end)

- Phase 0: `nmmb_hst_01_nio_0084h_00m_00.00s` exists for an archived cycle; UPP produces grid-218 GRIB2 readable by wgrib2; 500 hPa heights and 6 h QPF plotted beside the archived `nam.tHHz.awphysNN.tm00.grib2` for the same cycle look alike.
- Phase 1: scorecard notebook over the case set: RMSE/bias tables recast vs archive vs GFS, verified against obs (ASOS/SNOTEL via existing wsis fetchers). Pass = recast beats GFS and tracks the archive at 12-84 h.
- Phase 2: four cycles a day for two weeks with alarms on missed cycles; latency logged per cycle; cost tracked under a `project=nam-recast` allocation tag with a monthly budget.

## Open questions for Joe

- Is this for wsis (a NAM-physics snow input), for the forecaster community (BUFKIT + maps), or both? It changes the product and the egress line.
- Domain: keep the native 954×835 North American parent (faithful, ~700 core-h) or cut to a CONUS-plus domain (~2-3× cheaper, no longer "the NAM")? Recommend native for Phase 0-1, decide after measuring.
- Region: us-east-1 puts GFS input and the NAM archive in-region and has hpc7g; us-west-2 is where everything else of ours lives.
