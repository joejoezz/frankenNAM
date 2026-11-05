# Related work: WOOF-NAM (recastsystems/woof-nam) compared with FrankenNAM

Surveyed 4-5 Nov 2026 from a read-only shallow clone at `~/data/external/woof-nam/` (commit
`f5e023a5`, 5 Nov 2026 01:33Z) and the GitHub API. Nothing from their tree was executed, built or
installed. Quotes are from their files at that commit; paths are relative to their repository.

## One-paragraph verdict

WOOF-NAM is **not another port of the NAM build**; it is a **from-scratch rewrite of the NMMB
dynamics and the NAM physics suite as CUDA kernels driven from Python (CuPy)**, by Recast Systems
(a San Francisco cloud-seeding start-up, seed-funded May 2026) on top of their existing GPU
WRF-class model "WOOF"/ArWen. It was published the day after the NAM retired (first commit
2026-11-04 17:31Z, "private snapshot of the port"), reads the same upstream source we do
(MatthewPyle-NOAA/NAM @ `83df4e13`, nam.v4.2.11), runs the same 954 x 835 x 60 parent with the
same configfile, and judges itself by maps beside the archived NAM and MRMS. It runs a 24 h
forecast in about 10 minutes on one 96 GB GPU. It is single precision, not bit-faithful, has no
post (no UPP, no GRIB2, no grid 218, no BUFKIT), no soil cycling, no operations, no verification
numbers, and its GFS-start path has no published evidence yet. It is a desktop/workstation tool
("run on your own card"), not a service. The two projects do not compete for the same thing today:
they rebuilt the model, we are rebuilding the product.

## Summary table

| | WOOF-NAM (recastsystems/woof-nam) | FrankenNAM (this repo) |
|---|---|---|
| What it is | CUDA/CuPy rewrite of NMMB dynamics + NAM physics, 321 "units", one `.cu` per Fortran routine | The NOAA Fortran (NPS + NEMS/NMMB + UPP) built and run as-is, with 12 small source patches |
| Source | MatthewPyle-NOAA/NAM @ `83df4e13c1` (nam.v4.2.11), read as a specification | Same repo and commit (primary), plus EricRogers-NOAA/nam_wcoss2_rocoto; S3 git bundles |
| Fix files | Radiation/CO2/ozone from NOAA `fix/am/20220805`; Noah tables are a **WRF stand-in** (NAM `VEGPARM.TBL` "never published"); terrain GMTED2010 via WPS_GEOG; no NPS geog, no CRTM | NAM `fix/` recovered from Wayback captures of nam.v4.2.9-11 (geog, Noah tables, CO2, etc.) |
| Licence | Apache-2.0; NOTICE declares NOAA public domain, AER BSD-3 for RRTMG, ArWen Apache-2.0, WRF tables; `licence-check` tool in CI | Upstream public domain; our scripts/patches in this repo (no licence file yet) |
| Precision/fidelity | float32 "with fast numerics", "Not bitwise with the NAM" | Same bits as ops within compiler roundoff (ifort x86 and gfortran arm64 agree at f00, roundoff growth after) |
| Platform | Linux x86_64 + NVIDIA (CUDA 13 driver), 1 card >= 32 GB or N cards of one machine (NCCL); no multi-node | AWS Graviton (c8g/m8g.8xlarge Spot, 32 cores) default; x86 oneAPI fallback |
| Build stack | Python 3.12, `cupy-cuda13x`, NVRTC at first use, `gpuwm>=2.9.11` (Rust GRIB2 decoder, NetCDF writer, renderer); no Fortran, MPI, ESMF, nemsio, NCEPLIBS, UPP | gfortran 13 + OpenMPI 4.1 (arm64) / ifort 2021.13 + Intel MPI (x86), ESMF 7.1.0r, 21 NCEPLIBS pins, wgrib2 3.1.3 |
| Our seven porting bugs | None apply: they have no ESMF, no MPI finalize, no NEMS internal state, no ungrib, no UPP, no wgrib2 | All hit and fixed (`build/patches/`, `docs/graviton-port.md`) |
| Initial condition | (a) archived NAM native analysis `bgrd3d00` (past cases only), (b) GFS 0.25 f000 of the **same cycle**, (c) ECMWF IFS open data; GPU re-implementation of metgrid/nemsinterp | GFS 0.25 f000 of **cycle - 6 h** with a 6 h NAM spin-up (tm06), product f00 at cycle time; NPS as ops |
| Boundaries | GFS cycle - 6 h, every 3 h, written as NPS `boco.NNNN` files (own GPU writer) | GFS cycle - 6 h (the start cycle), every 3 h, through metgrid/nemsinterp |
| DA | None; `USE_RADAR 0`; honest that the archived start is "the cycled NDAS/GSI state" | None; honesty line on every product |
| Soil / land cycling | None: GFS start takes GFS soil ("declared fills"); native start takes the analysis soil | Noah soil/skin/snow seeded from the archived NAM (hindcast) or our previous run (live) through a second metgrid source |
| Nests | Not ported (named gap) | Not built (parent only) |
| Domain / dt | 954 x 835 x 60, dt 25 s, TDFI 600+600 s at 8 s; also experimental 4 km (1371 x 1101) and 5 km grids on their CONUS footprint | Same parent, dt 25 1/3 s as ops, TDFI |
| Forecast length | Examples 6-48 h; `--hours 84` appears in the restart example | 84 h product (90 h integration) |
| History / output | Hourly wrfout-shaped NetCDF (one file/hour, ~190 MB per 3-D field uncompressed), PNG maps (7 products), `forecast-receipt.json` | nemsio history 3-hourly, UPP, grid-218 GRIB2 `awphysFF` inventory-identical to ops (454 records), `.idx` |
| Post | In-model QUASIPOST membrane MSLP; no UPP, no GRIB2, no soundings/BUFKIT ("soundings come from history files") | UPP (`ncep_post`), wgrib2 products, BUFKIT planned |
| Speed | 24 h in 615 s on one RTX PRO 6000 96 GB (178 ms/step); 339 ms/step on one RTX 5090 32 GB; 53 ms/step on 8 x 5090 | 200 s per forecast hour on 32 Graviton4 cores (84 h in 4.7 h); x86 189 s/h |
| Cost per run | Not published (own hardware); a 96 GB card would do 84 h in ~36 min | $2.35 per 84 h on c8g.8xlarge Spot |
| Restarts | Hourly restart sets, 15.3 GiB, byte-identical resume (one card only) | NMMB restarts available (128 GB nodes), off by default |
| Verification | Side-by-side maps vs archived NAM and MRMS for one case (2025-03-14 12Z severe outbreak), native start, +12/+24 h; no scores | Phase 0 grid-to-grid RMSE/bias vs archived NAM and GFS; baseline scorecard vs ASOS/MRMS/SNOTEL; Phase 1 hindcast |
| Operations | None (CLI tool, user's own GPU) | Spot runners, S3 queue, relay, delivery clock C+3:10, Phase 2 scheduling |
| Maturity | Created 4 Nov 2026, 17 commits in 8 h, 1 release v0.1.0, 4 stars, 0 forks, 0 issues, 0 listed contributors (commits by "woof-nam package <package@localhost>") | Started 3 Nov 2026, Phase 0 and Graviton port done, Phase 1 in progress |
| Business | Apache-2.0 open source; company sells cloud seeding, not forecasts; no site, no pricing for WOOF-NAM | Free maps + $14.99/month grids planned (docs/product-plan.md) |
| Name | "WOOF-NAM", `woof-nam` on PyPI (reserved, not uploaded yet), import `namgpu`; NOTICE: "not affiliated with or endorsed by NOAA, NCEP or EMC" | "FrankenNAM", "a community recast of the retired NAM"; product file names identical to ops `nam.tCCz.awphysFF.tm00.grib2` |

## 1. Provenance

- Source: "Source of truth for numerics is the NAM clone at `$NMMB_SRC`
  (`<NAM clone>/sorc/nam_nems_nmmb.fd/src/atmos`) ... (nam.v4.2.11, 83df4e13c1)" (`CONTRACT.md`
  l.4-7); NOTICE: "The port is written from the NAM source (github.com/MatthewPyle-NOAA/NAM @
  83df4e13c115d197db67b972cb3befec8511291a, nam.v4.2.11)". That is exactly our primary upstream
  commit (`docs/build-notes.md`). They do not mention the NCO tree, the Rogers rocoto repo or DTC.
- They did not take the Fortran with them: "No code from the NEMS framework, ESMF, nemsio, UPP, GSI
  or NCEPLIBS (LGPL and other terms) is ported, copied, linked or called" (NOTICE). Every kernel
  header is required to carry "`// Ported to CUDA for WOOF-NAM from <path>:<lines> (nam.v4.2.11,
  83df4e13c1).`" (`CONTRACT.md` section 3).
- Fix files: `namgpu/data/fix/PROVENANCE.txt`: "Unmodified copies of the NOAA global fix set,
  fix/am/20220805, from https://noaa-nws-global-pds.s3.amazonaws.com/fix/am/20220805/" (CO2
  history, ozone climatology, solar constant, emissivity index). Noah tables:
  "the NCEP NAM fix VEGPARM.TBL (IGBP first, old 10-column layout) is not published anywhere we
  can fetch. This builds the IGBP rows from WRF V3.0's MODIFIED_IGBP_MODIS_NOAH section"
  (`namgpu/data/fix/noah/PROVENANCE.txt`), flagged as a "NAMED GAP: replace with the NCEP NAM fix
  tables when found". **We have those tables** (recovered from Wayback with the rest of `fix/`).
  GWD terrain comes from GMTED2010 via a WPS geog set, "ocean = 0 m, not -9999: declared difference
  from NPS" (`CONTRACT.md` section 8). NAM parm files are shipped "unmodified" (`namgpu/parm/`:
  `nam_configfile`, `nam_solver_state.txt`, `nam_phy_state.txt`, `nam_namelist.nps`, Vtable).
- Static surface for a GFS start is not geogrid: it is cut from any archived `bgrd3d00` once
  (`woof-nam static`, 1.4 MB npz), so land mask, soil/veg type and terrain are the operational
  NAM's own fields on its own grid. Clever and cheap; it also means the static fields are frozen
  at whatever that analysis carried (albedo, greenness are time-of-year).
- Licensing: Apache-2.0 for their code (`LICENSE`, `pyproject.toml`), a careful `NOTICE` with an
  origins table, AER BSD-3-Clause applied to the RRTMG-derived kernels and tables (108 files,
  commit `1a3e4c2b`), WRF public-domain notice for the Noah tables, ArWen Apache-2.0. A CI step
  (`tools/licence_check.py`) fails the build if an AER-derived file lacks its header. The LGPL
  `mersenne_twister.f` was deliberately re-implemented from the paper. This is more licence
  hygiene than most NWP projects have.

## 2. Build stack

There is no build in our sense. `pyproject.toml`: `requires-python = ">=3.12"`, dependencies
`cupy-cuda13x[ctk]`, numpy, scipy, netCDF4, Pillow, `gpuwm>=2.9.11`. README: "No system CUDA
toolkit is needed ... The kernels are compiled on the card at first use (NVRTC) and cached."
Numerics: "NVRTC with `--fmad=true` (FMA on), IEEE division/sqrt, no `--use_fast_math`. `float`
everywhere the Fortran is `kfpt`; `double` only where it declares `kdbl`" (`CONTRACT.md` section 3).
Note NAM's `kind_phys` is 8 bytes for the radiation; they store those planes as float32, "a declared
divergence, bounded per unit" (`CONTRACT.md` 1b).

Platform: "Linux (x86_64) with Python 3.12 or newer", "An NVIDIA card with 32 GB (one RTX 5090) or
larger; up to 85 GB on a 96 GB card without the fit", or several cards of one machine over NCCL
(README "What you need"). Multi-node is a named gap. State size: "the full state (48 3-D fields at
60 x 835 x 954 x 4 B = 191 MB each) is about 10.6 GiB" (`CONTRACT.md` 1); the forecast pool ended at
74 GiB on the 96 GB card, so the "32 GB fit" releases arrays between steps and chunks the radiation.

Patches to upstream: none, because nothing upstream is compiled. **None of the seven problems we
fixed can occur in their design**: no ESMF (icpx/aarch64 patches), no MPI (`MPI_Finalize` hang), no
NEMS solver internal state (`MY_DOMAIN_MOVES`), no ungrib (edition detection), no UPP (`size()` on
null pointers), no wgrib2 (`-new_grid` on template 32769). They have their own class of bugs
instead; `CONTRACT.md` section 10 records one: "LW setcoef: the COLAMT macro now reads the value
(it returned the flat index, which made every LW optical depth ~1e3-1e4 too large)". Their
multi-card work found the same thing we found about reproducibility: "A fresh init is not
bit-repeatable, because two of its sums use float atomics", and they solved domain-wide sums with
fixed-order row partials so N cards give the same bits as one.

Third-party physics: MYJ PBL, Janjic surface layer and Noah are adapted from ArWen's WRF-lineage
kernels (mode "copy-arwen"), then "brought to the NAM Fortran". Their own note:
"the NAM MYJ copy is ~26% line-identical to WRF v4.7.1, the NAM JSFC ~80%, and NAM Noah carries the
NCEP v4 changes (frozen-soil transpiration, reduced roughness for five vegetation types) that WRF's
Noah lacks" (`namgpu/third_party/arwen/README.md`). Whether every NCEP change made it across is
exactly the kind of thing their "no bitwise campaigns" rule (`CONTRACT.md` section 0) cannot tell.

## 3. Initialisation and cycling

- Three start sources (`namgpu/init/sources.py`): `native` (archived `nam.tHHz.bgrd3d00.tm00.grib2`,
  "Same grid and levels as the model: no interpolation", "valid_before 2026-11-03T12"), `gfs`
  (GFS 0.25 `pgrb2.0p25.f000` of the cycle itself), `ifs`/`ifs-0p25` (ECMWF open data, CC BY 4.0,
  added 5 Nov 01:00Z). HRRR and RRFS rows exist but are "refused by name today" (Lambert grids not
  decoded). They note the archived start is "the cycled NDAS/GSI state the operational NAM forecast
  started from" (`init_native_atm.py`), i.e. their showcase case starts from the real NAM analysis
  and so inherits the DA, which a live run cannot.
- **Same-cycle start, no spin-up.** `woof-nam run --case 2026-11-04_12z --source gfs` starts from
  the 12Z GFS analysis at 12Z. That is our Phase 0 "anl" arm, not our tm06 product. The boundaries
  come from "the GFS cycle 6 hours older, as in the operational NAM" (README "Scope"), so the
  start is newer than its boundaries, as in ops.
- NPS replacement on the GPU: `gfs_start.py` ("metgrid-style columns ... by init-gfs-hinterp
  (four_pt + average_4pt), then nemsinterp's vertical interpolation"), `gfs_bocos.py` writes
  `boco.NNNN` "in the format NPS writes and READ_BC reads" with the exact record layout
  (`module_boundary.F90:630-1366`). They re-derived NPS's vertical coordinate ("gfs_start.ensure_vcoord
  (the NPS vcgenerator header, vcoord = 1)").
- Soil: a GFS start takes GFS soil "in the same four Noah layers" with "soil fields where the source
  is water but the NAM grid is land ... filled from the nearest source land"; the 3 m soil
  temperature "is the source's 1-2 m layer (GFS has no 3 m level)". No seeding from the NAM, no
  run-to-run cycling, no snow-depth special handling beyond the source fields. Shelter fields
  (T2/Q2/U10) are filled from the source's own 2 m/10 m analysis rather than left at NMMB's
  cold-start defaults, a detail we get through nemsinterp.
- DA: none, and nothing planned in the tree. `config.py`: `"USE_RADAR": "0", # no GSI radar heating
  (we start from the archived analysis)`, `"PFLAG": "false", # no precip assimilation`.
- Nests: "the NAM's nests (CONUS 3 km, Alaska, Hawaii, Puerto Rico, fire weather) are not ported;
  this is the 12 km parent only" (README "Known gaps"). They do run the NAM dynamics on a 4 km
  1371 x 1101 grid over the CONUS-nest footprint with GFS boundaries (not a nest, a standalone
  domain): "24 h on 8 RTX 5090 cards (42.9 ms per step, 522 s wall)".

## 4. Domain, resolution, cadence, products

Configuration is the operational parent read from the unmodified `nam_configfile` with the
`exnam_fcst.sh` substitutions for a tm00 free forecast (`config.py SCRIPT_SUBSTITUTIONS`:
`FILTEROPTION 3`, `PRECIPBUCKET 3`, `NUMDOM 1`, ...). `CONTRACT.md` section 5 tabulates it: IM 954,
JM 835, LM 60, centre 54 N / -106 E, PT 200 Pa, dt 25 s, NPHS 2, NPRECIP 2, NRADS = NRADL 48, BMJ,
Ferrier-Aligo, MYJ, Noah (IGBP), RRTM, GWD on, TDFI 600 + 600 s at 8 s, `minutes_history 60`.
One difference from ops: they take `dt_int 25` as 25 s; ops runs 25 1/3 s (`dt_num 1, dt_den 3`
in our `docs/scoping.md`; their `CONTRACT.md` says "`dt_num: 0`" in the configfile they hold, so
this may be a configfile version difference, worth a check against our parm copy).

Output is hourly "wrfout-shaped NetCDF": XLAT/XLONG, HGT, PSFC, T2, Q2, MSLP (membrane), U10/V10
(earth-relative), RAINNC/RAINC, T, QVAPOR, QCLOUD/QRAIN/QICE/QSNOW, PH, PRES, U/V/W on mass points,
REFL_10CM and COMPOSITE (`io/history.py`). Maps: composite reflectivity, 2 m T and Td, 10 m and
850 hPa wind, MSLP, 1 h QPF (`io/maps.py`), drawn by gpuwm's Rust renderer. Hourly maxima
(`io-max-fields`, UPHL) are listed as `todo`. **No GRIB2 output, no grid 218, no UPP fields, no
soundings, no BUFKIT.** The in-model MSLP is the QUASIPOST membrane MSLP, which is the field the
NAM's `MSLET` record carries, not the UPP Shuell PRMSL.

## 5. Operations

None. The package is a CLI for one machine: "Run every command from one working folder". Their
own box tooling (card leases, locks) is explicitly disabled for outsiders (`WOOF_NAM_BOX=1`). No
cloud provider, no scheduler, no delivery clock, no cost numbers. Speed numbers that matter for a
would-be operator (README "Speed and memory"):

- "**24 h forecast:** 3,456 steps in 615 s, 178 ms per step (all physics, hourly history); 731 s for
  the whole `woof-nam run`" on one RTX PRO 6000 96 GB.
- One RTX 5090 32 GB: "1,728 steps in 586 s, 339 ms per step".
- 8 x RTX 5090: 53-55 ms/step, "92 s" for 6 h.

Scaled, an 84 h parent run is ~36 min on one 96 GB card, ~68 min on one 5090, ~11 min on eight.
Our 84 h is 4.7 h on 32 Graviton cores. If one wanted this on AWS: a g6e.xlarge (L40S 48 GB) is
~$1.86/h on-demand, so an 84 h run would be ~$1 at their 96 GB pace if the fit path costs nothing,
which it does not (339 vs 178 ms/step). Spot GPU capacity is far scarcer than Graviton Spot.

Restarts: `--restart-every 1h` with a byte-identical `--resume` (proved with SIGKILL after the 3 h
set; "all 7 hourly history files ... are byte-identical"), 15.3 GiB per set written by a background
thread. One card only.

## 6. Verification and claims

- Rule: "Not a bitwise port ... No bitwise campaigns, no column tests, no dry/adiabatic runs. The
  proof of the port is the whole 12 km forecast with all physics on, judged by maps beside the
  archived NAM forecast of the same cycle and MRMS" (`CONTRACT.md` section 0). "Scores beside the
  pictures, not instead of them" (`cases/2025-03-14_12z/CASE.md`), but no scores are published.
- Evidence: one case, 2025-03-14 12Z (Plains/Mid-South severe outbreak, the same case we picked
  for our hindcast list), **native-analysis start**, +12 and +24 h sheets of composite
  reflectivity (MRMS | WOOF-NAM | NAM), 2 m T and total precipitation (WOOF-NAM | NAM)
  (`docs/evidence/`). Their caption: "like the NAM, WOOF-NAM wraps the comma head over the upper
  Midwest and puts the trailing line west of the observed one, and neither model has MRMS's second
  band across Mississippi and Alabama." My read of the +24 h reflectivity sheet: the comma head and
  the Pacific NW precipitation match the NAM's shape and placement well; the WOOF-NAM panel has
  much less of the NAM's light reflectivity over the Gulf Coast, Southeast and western Atlantic,
  and its trailing band is weaker and less organised. The 2 m T panels are very close. Reasonable
  for a day-old port; not yet evidence of statistical fidelity.
- There is **no published GFS-start result**, and the GFS start is the only one that can run live.
  Since the CASE.md note says "our initial state is that same analysis on its native grid, so the
  two runs start from the same state", the showcase comparison measures the dynamics/physics port,
  not what a user would get after 3 Nov 2026.
- Honesty: good on affiliation (NOTICE: "It is not affiliated with or endorsed by NOAA, NCEP or
  EMC"; "It is not permissible to state or imply endorsement by or affiliation with NOAA") and on
  precision ("Not bitwise with the NAM"). The DA situation is stated only indirectly ("the archived
  NAM is a forecast from the NAM's own GSI/NDAS analysis"); there is no equivalent of our honesty
  line for a GFS-start run, and README's "this package keeps the model running" elides the
  difference between the model and the forecast system.

## 7. Maturity and community

- Repository created 2026-11-04 17:31:52Z; 17 commits between 17:31Z and 01:33Z the next day, all
  authored "woof-nam package <package@localhost>" (the GitHub contributors list is empty). First
  commit: "woof-nam 0.1.0: NAM 12 km (NMMB) on the GPU, private snapshot of the port at
  a9ddf55/ea8c370" (159,583 lines added), so the work happened in a private repo; `CONTRACT.md`
  dates its sections 2026-11-03 and 2026-11-04, and the physics "first ran on the real 2025-03-14
  12Z state" at "2026-11-04 ~09:50Z". The whole port appears to be days old, almost certainly
  agent-written at scale (321 units with uniform headers, "lanes", "integrators", "owner ruling",
  "judge phase" vocabulary throughout `CONTRACT.md`).
- Release v0.1.0 (2026-11-04 22:14Z); PyPI trusted-publisher workflow exists but upload is gated
  ("PyPI upload enabled only on the owner's yes"); `woof-nam` is not on PyPI as of 5 Nov. 4 stars,
  0 forks, 0 issues, no topics, no homepage. Nothing runs live anywhere.
- The organisation: Recast Systems (github.com/recastsystems, blog recastsystems.com, created June
  2025, 8 public repos, 13 followers). Their site: "Recast is a weather company building precision
  weather modification ... Today, we perform weather modification via cloud seeding"; job listings
  in San Francisco; "2026 Season Recap ... cloud seeding operations in New Mexico and Texas".
  PitchBook (via search) lists a seed round 1 May 2026 (Asylum Ventures), 6 employees. Their main
  model repo `recastsystems/woof` (64 stars, 13 forks, releases v1.0.0 30 Sep to v1.1.5 31 Oct 2026)
  is committed by Andrew Snyder <andrew@recastsystems.com>; WOOF "continues an engine released
  before under another name" (ArWen, PyPI `gpuwm`, github.com/FahrenheitResearch/arwen, 17 stars).
  Other repos: `recast-wxmod` (AgI seeding physics for WRF), `recast-radar-tools` (Rust NEXRAD
  toolkit), `hermes-woof` (an LLM-agent plugin to run WOOF).
- Business model for WOOF-NAM: none visible. The company's product is cloud seeding; the models are
  Apache-2.0 tools, probably for their own operations, recruiting and credibility. Nothing suggests
  a forecast subscription.

## 8. What we could learn or reuse, what each side does better, coordination

Reusable under Apache-2.0 (attribution + NOTICE carried along):
- **Their map/side-by-side convention** is good: same frame, same colour scale, MRMS | ours | NAM,
  one sheet per product and hour, hourly. Our `compare.py` panels are 4-up on 0.25 deg; a
  reflectivity sheet against MRMS at native resolution would strengthen the Phase 1 feature-
  fidelity gate. The renderer itself is Rust inside `gpuwm`; not worth importing, the idea is.
- `cases/2025-03-14_12z/CASE.md` is a tidy case-file format (why this day, inputs with sizes and
  URLs, referees, declared differences). Worth copying the shape for `docs/cases.md`.
- Their `fetch_case.py` pulls hourly `awphys` subsets by `.idx` byte ranges and MRMS
  `MergedReflectivityQCComposite_00.50` nearest each hour; our `verify/` already does MRMS QPE,
  not composite reflectivity. Cheap to add.
- Their NOTICE/licence-check discipline is a model if we ever publish our patches and scripts.
- `SCRIPT_SUBSTITUTIONS` in `config.py` is a clean statement of what `exnam_fcst.sh` sets for a
  free forecast; a useful cross-check of our `recast.sh` configfile edits (buckets 3 h, `RESINT`,
  `WRTLAST`).
- Not reusable: kernels, state layout, anything that needs a GPU. Nothing in their tree helps our
  build, NPS, UPP or wgrib2 problems.

What they do better:
- Speed and hardware economy for a single run (24 h in 10 min on one card; 84 h in ~36 min). If
  the project ever needs sub-hour delivery or many members, GPU is the path, and they have shown the
  NMMB parent fits one card.
- Packaging: `pip install`, one command, everything in the wheel, byte-identical restarts and
  multi-card reproducibility checks, CI on every push.
- A second, independent start source (IFS open data) in a day.
- Licence and provenance bookkeeping.

What we do better:
- Fidelity: it is the NAM's own code, with ifort/gfortran agreeing to roundoff; theirs is a
  float32 rewrite judged by eye. For a product whose only selling point is "the NAM's physics
  back", that matters.
- The product: tm06 spin-up so f00 is at cycle time, soil seeded and cycled from the NAM, UPP, the
  full awphys inventory on grid 218 with `.idx`, ops file names, a delivery clock, Spot economics
  ($2.35/run), verification against observations, a baseline scorecard. They have none of this.
- Honesty line and an explicit account of what the DA was worth (Phase 1 arms).
- Fix files: we have the real NAM Noah tables and geog; they are using a WRF stand-in and know it.

Coordination: **not now.** Different goals (tool vs service), different fidelity bars, a company
with other priorities, and a repo that is hours old with no community. The one concrete thing
they lack that we have is the NAM `fix/` set (Noah `VEGPARM.TBL` etc.), which is US-government
public domain and could be pointed to publicly without "contacting" anyone, if Joe wants to be a
good citizen later. Revisit in a few months: if they publish GFS-start scores and the port holds
up, a GPU FrankenNAM runner (same inputs, same products, our post on their history) would be a
cheap experiment, and their renderer/case tooling could be adopted. I would not build on their
kernels for the product before an independent verification exists.

## 9. Overlap with our name and positioning

- They use "NAM" prominently: repo `woof-nam`, product "WOOF-NAM", PyPI name `woof-nam`, map
  titles "WOOF-NAM 12 km", README "the NAM 12 km (NMMB) model ported to the GPU". So does
  "FrankenNAM". NAM is a NOAA model name, not (to our knowledge) a registered mark; both projects
  carry a non-affiliation statement. Theirs is in NOTICE and README; ours is the honesty line on
  every product page. No conflict between the two names.
- Their README opening ("NCEP retired the NAM on 2026-11-03 12Z; this package keeps the model
  running") is the same resurrection story we tell. Expect journalists or forecasters who find one
  to ask about the other. Our differentiator in one sentence: *FrankenNAM runs the NAM's own code
  as an operational product with verified fidelity; WOOF-NAM is a GPU rewrite you run yourself.*
- One thing to watch: they reproduce NOAA's unmodified `parm/` files and NOAA headers in every
  kernel, and state NOAA public-domain status explicitly. We should add a `LICENSE`/`NOTICE` to our
  repo before anything is public (upstream public domain; our patches and scripts under a licence
  of Joe's choosing; AER's RRTMG notice applies to any redistribution of the radiation source, which
  our build tarballs technically are).
- Their file names (`wrfout_d01_*`) do not collide with the ops names we duplicate; ours are the
  only drop-in replacement for `nam.tCCz.awphysFF.tm00.grib2` consumers.

## What this means for FrankenNAM

1. **No change of course.** They have rebuilt the engine; we are rebuilding the forecast system.
   Nothing they published shortens Phase 1 or Phase 2, and nothing in their tree fixes anything in
   our build.
2. **Fidelity is our story; say it.** We can state "the NAM's code, bit-for-bit modulo compiler
   roundoff, verified against the archive and observations" and they cannot. The scorecard page
   should say this plainly, without naming them.
3. **Adopt two cheap things:** MRMS composite-reflectivity sheets at native resolution in the
   Phase 1 case comparisons (MRMS | FrankenNAM | NAM, same frame and scale), and the CASE.md
   case-file shape. Both fit `verify/` and `docs/cases.md` without new dependencies.
4. **Add LICENSE/NOTICE to our repo** before the site goes live; their NOTICE is a good template
   for the NOAA public-domain and AER RRTMG statements.
5. **Keep a note for later:** a GPU runner is a real option if delivery time or ensemble members
   ever matter, and WOOF-NAM proves the parent fits one card. Re-check their repo in Dec 2026
   for GFS-start evidence, scores, live use and PyPI release; until then do not depend on it.
6. **Do not contact them now.** If Joe wants, a public pointer to where the NAM `fix/` tables can
   be recovered (Wayback) would help them and costs nothing; it is not required.

## Addendum, 5 Nov 2026 03:48Z: they are serving free GRIB2
`https://woof-nam.recastsystems.com/` lists runs with downloadable files. Facts read from the index,
`status.json`, a run directory and their `README.txt` (which is marked "NOT PUBLIC" draft with
placeholder dates):
- Free; proposed licence CC BY 4.0 "WOOF-NAM by Recast"; "not an official NOAA/NWS forecast", no warranty.
- "A one-week public run" (dates are placeholders); files deleted after 7 days.
- Four cycles a day, f00-f84 **hourly**, grid 218, awphys-style inventory (some fields "not yet
  included"), `.idx` per file, `cycle.json` with SHA-256, PNG maps every 3 h.
- File names `woof-nam.tHHz.awphysFF.tm00.grib2`: deliberately **not** drop-in for NOAA tooling.
- Files are ~175 MB each (NOAA's are ~58 MB): packing "undecided, complex or lossless"; a cycle is
  15.6 GB, so a user pulling four cycles a day moves ~62 GB/day.
- Start: same-cycle GFS 0.25° analysis, GFS boundaries, no DA, no spin-up, no soil seeding.
- Clock: run starts ~C+3:30 when the GFS lands, all 84 h ~C+4:20 (observed 00Z 5 Nov: first file
  C+3:39, 20 h done by C+3:48, i.e. ~27 s per forecast hour on the GPU). The 18Z 4 Nov run
  completed at C+9:04 (late start). Next run advertised for 10:20Z.
- No verification, no statement of hardware or who pays.

What it means: a free hourly GRIB2 feed exists today from a float32 rewrite of unknown fidelity,
framed as a one-week demo, with a different file prefix and 3x the bytes. FrankenNAM's
differentiators stand: the NAM's own code with measured fidelity to the archive, NOAA-identical
names, the tm06 clock (f24 before cycle time, f84 ≈ C+2:57 vs their C+4:20), seeded/cycled soil,
operations with verification and alerts. Decision (Joe, 5 Nov): stay the course; re-check in two
to three weeks whether the feed persists past the demo week and whether they publish skill.
