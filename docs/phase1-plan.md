# FrankenNAM Phase 1: plan and budget (4 Nov 2026)

Phase 0 proved the model builds, runs the full 12 km parent for 84 h on one 32-core Spot node
in 4 h 25 min (≈ $4), and on one case tracks the archived NAM more closely than the GFS does
through 48 h (`docs/phase0-case-2026110100.md`). Phase 1 turns that into the product
configuration and measures it properly. Decisions already taken: name FrankenNAM; GFS-only inputs;
00Z/12Z cycles; match the old NAM delivery clock via the tm06 spin-up design
(`docs/scoping.md`, "Decisions after Phase 0").

## Goal and gate

**Goal:** a validated FrankenNAM configuration, with a scorecard and a demonstrated delivery
clock, ready to be put on a daily schedule in Phase 2.

**Gate to Phase 2 (rewritten 4 Nov 2026 after the baseline scorecard; Joe agreed):**
The operational NAM did not beat the same-cycle GFS against observations on the seven cases
(`docs/baseline-scorecard.md`), so "beat the GFS" was the wrong bar. FrankenNAM is a resurrection;
the gate is **fidelity**, reported honestly with the GFS alongside for context:
1. **Statistical fidelity:** on the hindcast set, FrankenNAM (tm06) against observations is within
   noise of the archived NAM: pooled 12-84 h CONUS 2 m T / Td / 10 m wind RMSE within 0.1 K /
   0.1 K / 0.1 m/s and 24 h precipitation ETS within 0.03 at 2.5/10/25 mm; biases of the same sign
   and size (the NAM's near-zero T/Td bias where the GFS runs warm and dry). Also: not worse than the
   6 h older GFS it starts from by more than those margins.
2. **Feature fidelity:** on each case FrankenNAM reproduces the archived NAM's key features that
   forecasters used it for: the CAD wedge's position and persistence, the snow/sleet transition
   timing in Snowcrete, the Gulf snow band, the PNW orographic maximum, the lake-effect bands, the
   Plains dryline/convective mode, in side-by-side panels with the NAM and the GFS.
3. One real-time dress-rehearsal cycle delivers f84 within ~3 h 10 min of cycle time on one
   c8g.8xlarge (the old NAM's 2 h 42 min is the target with more cores), and products open in
   standard tools under the NAM's own file names.
The scorecard page says all of this plainly: FrankenNAM is the NAM's physics with a GFS start, it
inherits the NAM's strengths (bias, soundings, mesoscale structure) and its weaknesses
(precipitation placement vs the GFS), and it is offered as an independent second opinion, not as a
GFS-beater.

## Workstreams

### W1. Product configuration: tm06 spin-up driver (the core of Phase 1)
- Start at cycle − 6 h from that GFS cycle's analysis (f000), integrate 90 h; hour 6 becomes
  f00 of the product. Boundaries from the same GFS cycle, f006-f090. 
- Boundary files produced while the model runs (ops `boco1` structure): launch needs only the
  analysis and the first boco. Measure the launch-to-start latency.
- Precipitation buckets aligned to the product clock (3 h buckets, 3-hourly history; hourly
  history timed on one case for later BUFKIT soundings).
- Product GRIB2 metadata: reference time = cycle time, fh 0-84 (what the old NAM did; its
  tm00 state was also a 06Z start plus 6 h). The honesty line goes in every product page/README.
- Noah land-state cycling from the previous FrankenNAM run (ops `exnam_sfcupdate` as spec);
  for hindcasts, seed from the archived NAM of the start time. Snow/SST from the GFS.
- Restart cadence vs the 77 GB write peak: keep ≥128 GB nodes (m7a/r7a.8xlarge) or spread the
  write ranks; measure both.
- Spot interruption: resume from the latest restart in S3 (runner already does this; test it by
  killing a run).

### W2. Hindcast: three arms, ~18 cases
- Arms per case: **archived NAM** (reference), **FrankenNAM tm06** (product), **FrankenNAM
  same-cycle analysis start** (reference: measures the 6 h information lag).
- Cases (all within the AWS NAM archive, Sep 2021 → Nov 2026; prefer the last two winters):
  6 winter storms (Nor'easter, Plains blizzard, Pacific NW atmospheric river, Sierra, Front Range
  upslope, Great Lakes), 2 cold-air damming / p-type, 2 arctic outbreak + lake effect, 3 spring
  severe, 2 summer MCS, 1 landfalling tropical system, 2 quiet. 00Z and 12Z mixed.
- Verification against **observations**, not only the archive: ASOS (2 m T/Td, 10 m wind, via
  the Iowa Mesonet archive), MRMS gauge-corrected QPE (AWS `noaa-mrms-pds`) for 6 h/24 h precip,
  SNOTEL for mountain precipitation (wsis fetchers), p-type where ASOS reports it. Plus the
  Phase 0 grid-to-grid stats against the archive and the GFS.
- Output: `docs/phase1-scorecard.md` with RMSE/bias/ETS tables by lead and region, 9-panel
  figures per case, and a one-page summary that becomes the public credibility document.

### W3. Products and post
- `wgrib2 -new_grid` failed silently on the rotated B grid in Phase 0; the likely cause is a
  wgrib2 built without IPOLATES. Rebuild with it, produce grid 218 (`awphys`-equivalent) and
  the native grid, with `.idx` files, named like the old NAM files for drop-in use.
- Zarr/Icechunk store of the same fields for our own use (wsis), one store per cycle.
- Time the whole post chain so it overlaps the forecast (UPP already runs concurrently).

### W4. Throughput and infrastructure
- **Quota:** the account allows 32 vCPU of Spot in us-west-2. One run at a time means the
  hindcast (36 FrankenNAM runs × ~5 h) takes ~8 days serial. Request 192 vCPU Spot (standard
  family) in us-west-2; with it the hindcast runs 6-wide in ~1.5 days. Joe files the request;
  the text is in the appendix.
- Hindcast batch runner: a queue of cases, one runner per case from the S3 bundle, results to
  S3, nothing on the laptop.
- Cost tags (`project=frankennam`), a monthly budget alarm, a per-run cost line in each run's log.

### W5. Graviton/gfortran port (recommend: defer to Phase 2 or later)
- At $4 per x86 run the port saves roughly $1.50 per run, ~$90/month at two cycles a day, for
  1-2 days of agent work and a numerical-validation burden (gfortran vs ifort differences in a
  2017 code). Graviton 8xlarge nodes have 64/128/256 GB (c8g/m8g/r8g) and count against the
  same 32 vCPU quota. Recommendation: skip in Phase 1, revisit when cycles run daily and the
  x86 Spot price or capacity becomes a problem. If Joe wants it in Phase 1 anyway it adds ~$30.

### W6. Dress rehearsal
- Once W1 and W3 work, run one live 12Z cycle end to end from the real-time GFS, timed, and
  publish nothing. Target: f84 by cycle + 2 h 45 min, products on S3 by cycle + 3 h.

## Budget

| Item | Basis | Estimate |
|---|---|---|
| Hindcast compute | 18 cases × 2 FrankenNAM arms × ~$4.50 (90 h on r7a.8xlarge Spot + NPS) | $160 |
| Development runs (W1, W3, W6: spin-up tests, soil cycling, restart kill test, dress rehearsal) | ~12 partial/full runs | $40 |
| Build box (x86, on-demand, agent dev time) | ~30 h × $1.64 | $50 |
| S3 (staged GFS inputs ~15 GB/case, GRIB2 15 GB/run, MRMS/ASOS subsets; history deleted after post) | ~1 TB peak for a month | $30 |
| Verification data pulls, misc requests | | $10 |
| Graviton port (only if kept in Phase 1) | c8g build box + 2 validation runs | $30 |
| **Total** | | **≈ $290 (≈ $320 with Graviton)**, ceiling **$450** |

Spot prices vary ±30 %; the ceiling absorbs that plus one hindcast re-run after a bug.
Phase 0 spent $10.60 against a $60 ceiling. Ongoing after Phase 1: ~$7/month S3 until the
history files are deleted (~$1/month after).

Time: about two weeks elapsed with subagents doing the build work and me supervising, assuming
the quota increase lands within the first few days (AWS usually answers in 1-2 days). Without
the quota the hindcast alone takes 8 days of wall clock and the total stretches to ~3 weeks.

## Sequence

| Week | Work |
|---|---|
| 1 | W1 driver (spin-up, streamed bocos, buckets, soil seed), W3 wgrib2/grid 218/Zarr, quota request filed, hindcast case list + verification data staged (parallel agent), one tm06 case compared against Phase 0 |
| 2 | W2 hindcast batch (needs quota), scorecard, restart kill test, W6 dress rehearsal, Phase 1 report |

## Decisions for Joe

1. Budget ceiling $450 for Phase 1 compute and storage.
2. File the EC2 Spot vCPU quota increase (us-west-2, "All Standard Spot Instance Requests",
   32 → 192). Needed for hindcast throughput; also gives latency margin later.
3. Graviton port: defer (recommended) or keep in Phase 1.
4. History cadence for the product: 3-hourly (cheaper, no BUFKIT) or hourly (BUFKIT soundings
   possible later, ~3× history volume during the run, deleted after post). Recommendation:
   hourly history on the dress rehearsal to measure; decide for Phase 2.

## Appendix: quota request text

Service Quotas → Amazon EC2 → "All Standard (A, C, D, H, I, M, R, T, Z) Spot Instance Requests",
region us-west-2, requested value 192. Use case: "Batch numerical weather prediction hindcasts
(FrankenNAM, a community recast of the retired NOAA NAM) on r7a/m7a Spot instances, up to six
8xlarge nodes concurrently, each job 4-5 h, S3 in/out, no public-facing service on the nodes."
Also raise "Running On-Demand Standard instances" to 96 if offered, for fallback.

## Revision 4 Nov 2026 (evening): Graviton first, lean budget under $50

Joe: the project rests on delivering runs as cheaply as possible; Phase 1 budget target < $50.

### What the Graviton port entails
Toolchain: gfortran 13 + OpenMPI (apt, Ubuntu 24.04 arm64); no Intel compilers on ARM.
The tree already has `src/conf/configure.nems.Linux.gnu` with the right semantics
(`-fdefault-real-8 -fdefault-double-8`, `-fconvert=big-endian`, `-fno-range-check`, `-O3`).
Two things it lacks versus the WCOSS2 Intel config: `-init=zero` (the code relies on
zero-initialised locals; use `-finit-local-zero`, and catch the rest with a debug build using
`-finit-real=snan -ffpe-trap=invalid` on the 3 h smoke) and `-fallow-argument-mismatch`
(GCC ≥ 10 rejects the MPI buffer mismatches a 2017 code is full of). Intel's `-fp-model precise`
maps to plain `-O2`/`-O3` without `-ffast-math`. NCEPLIBS, netCDF, CRTM, bufr all build with
gfortran (that is their CI). NPS and UPP have GNU stanzas from their WPS/UPP ancestry.
**Main risk: ESMF 7.1.0r on aarch64** (its build system predates arm64 Linux; fallback is ESMF 8.x
with small NEMS API patches). Validation: same 2026-11-01 00Z case on Graviton vs the x86 run vs
the archive (differences should be roundoff at f00 growing to tenths of hPa/K by f84, within the
x86-vs-archive error), plus bit-for-bit reproducibility between two Graviton runs. Keep the
Intel-MPI barrier patch (harmless). Effort 1-2 agent days; ~$12.

### What it is worth, with today's Spot prices (us-west-2, cheapest zone, 4 Nov 2026)
| Node (32 cores) | RAM | Spot $/h | 90 h run at Phase 0 speed |
|---|---|---|---|
| r7a.8xlarge (Phase 0) | 256 GB | 0.82 | $4.10 |
| m7a.8xlarge | 128 GB | 0.61 | $3.05 |
| c7a.8xlarge, restarts off | 64 GB | 0.58 | $2.90 |
| c8g.8xlarge Graviton4, restarts off | 64 GB | 0.47 | $2.35 if gfortran matches ifort speed; $2.90 if 25 % slower |
| m8g.8xlarge Graviton4 | 128 GB | 0.53 | $2.65-3.30 |

Honest reading: the earlier "Graviton halves the cost" came from 48xlarge prices and does not
hold at 8xlarge; here Graviton is 15-20 % cheaper per hour and gfortran code is usually 10-25 %
slower than ifort, so the port saves $0-0.60 per run. The bigger levers are free: drop the
r-class node (restarts off, 64 GB c-class; a Spot reclaim then costs a $3 rerun, which at
typical interruption rates is pennies per run) and pick the cheapest zone at launch. The port's
real value is **capacity and price diversity**: two instance families and eight Spot pools
instead of four, and a hedge against x86 Spot spikes. Floor for daily operations at 00Z+12Z:
about $150-180/month compute for the full parent domain; nothing short of changing the model
(domain, levels, time step) goes below that.

### Lean Phase 1 (target < $50, ceiling $60)
| Item | Runs | Cost |
|---|---|---|
| Graviton port: Spot c8g.4xlarge dev box ~10 h, three 3 h smokes, one 84 h validation run on c8g.8xlarge | | $12 |
| Restarts-off / 64 GB memory check (part of the validation run) | | $0 |
| tm06 spin-up driver, streamed bocos, buckets, soil seed: short 6-12 h tests + one full 90 h run of the Phase 0 case | 8 short + 1 full | $8 |
| Hindcast: 5 new cases, tm06 arm (+ the Phase 0 case = 6) | 5 | $15 |
| Analysis-start reference arm on 2 of those cases | 2 | $6 |
| Dress rehearsal, one live 12Z cycle | 1 | $3 |
| S3 (transient ≤ 200 GB), MRMS/ASOS pulls | | $4 |
| **Total** | | **≈ $48** |

What is cut and what it costs us: the hindcast shrinks from 18 cases to 6, so the Phase 1
scorecard is indicative, not a verdict; no on-demand x86 box time (all development on Spot
Graviton nodes from the S3 bundle); no quota increase needed (6 serial runs fit in a week).
The verdict then comes from **live verification from day one of Phase 2**: at ~$6/day, the
first month of 00Z/12Z cycles is 60 verified runs, more than any hindcast we would pay for,
and it is the product anyway. Phase 2 must therefore ship the verification pipeline with the
first cycle, not after.

Standing cost to kill: the stopped x86 build box's 300 GB EBS volume costs ~$24/month, half
the Phase 1 budget. Everything on it is reproducible (`build/build_all.sh`, 17.5 min; binaries
and the 12.5 GB runner bundle are in S3). Recommendation: terminate it once the Graviton box
exists; keep a Graviton dev box only on Spot and only while an agent is working.

Cleanup done 4 Nov: Phase 0 history (203 GB) and the duplicate GRIB2 set (32 GB) deleted;
bucket now ~60 GB (~$1.40/month): x86 reference GRIB2 (16 GB, needed for the Graviton
validation), staged GFS/NAM inputs for the case (25 GB), fix files, runner bundle, figures.

## W5 Graviton port: DONE 4 Nov 2026 (details in `docs/graviton-port.md`)
Whole stack builds on arm64 with gfortran 13 + OpenMPI 4.1, ESMF 7.1.0r kept (three new patches),
eight patches total, every one explained. Validation on the Phase 0 case: 84 h in 16,811 s on
c8g.8xlarge Spot ($0.466/h) = **$2.35 per run** vs $3.80 on the x86 r7a; 200 s per forecast hour
vs 189 on x86 (6 % slower, within noise of the price gap); peak 43 GB, fits 64 GB with restarts
off; bit-reproducible run to run; identical to x86 at f00, roundoff divergence to tenths of hPa/K
by f84, same skill vs the archived NAM. Three latent upstream bugs surfaced (uninitialised
MY_DOMAIN_MOVES, ungrib edition detection, UPP size() on null pointers), all fixed at source.
**Decision: arm64 c8g.8xlarge Spot, restarts off, is the default runner; x86 path kept and
exercised as fallback.** Spent $9.4 of the $15. Both build boxes stopped.

## Next: Phase 1 step 2 (laid out 4 Nov 2026 evening, after the Graviton port)

Everything below runs on arm64 (c8g.8xlarge Spot, restarts off, $2.35 per 84 h). Remaining
budget ≈ $38 of the $50 target. Three agent briefs in sequence, A → B → C.

### A. The product configuration: tm06 spin-up driver, soil seeding, products (~$10, ~1 day)
1. **tm06 cycle in `run/recast.sh`:** for product cycle C, inputs are GFS cycle C−6: f000 as IC,
   f003…f090 as bocos (all 3-hourly). Integrate 90 h; integration hour 6 = product f00. History
   3-hourly (hourly timed once in C). 3 h precipitation buckets so the product's accumulations
   can be rebuilt on the C clock.
   *Simplification found while laying this out:* the whole C−6 GFS (to f090) is on AWS by about
   C−2:00 (f084 landed at +3:57 in the 3 Nov check), so **streamed boundary files are unnecessary**
   for the clock; NPS runs the IC as soon as f000 lands (C−2:15) and the bocos right after.
   Expected clock on one 32-core Graviton node: model start ≈ C−2:00, f24 products ≈ C−0:15
   (yes, before the nominal cycle time), **f84 ≈ C+3:10**, against the old NAM's C+2:42. A
   48-core node (c8g.12xlarge, 96 GB) would bring f84 to ≈ C+1:45 if scaling holds; that needs
   the Spot vCPU quota raised from 32 to 64 (free to request; recommended now).
2. **Product labelling:** UPP writes reference time C−6 and fh 6…90; a product step rewrites each
   GRIB2 to reference time C, fh 0…84, with `wgrib2 -set_date/-set_ftime`, and builds the 12 h and
   run-total APCP records the old `awphys` files carried from the 3 h buckets. Honesty line in the
   product README and the index page.
3. **Soil seeding/cycling through metgrid (one mechanism for both uses):** ungrib a second GRIB2
   source carrying the four Noah soil layers (0-10/10-40/40-100/100-200 cm, the same layering as
   the GFS), snow depth/SWE, canopy water and skin T, and let metgrid prefer it over the GFS for
   those fields. In hindcasts the source is the archived NAM `awphys00` valid at C−6; live, it is
   FrankenNAM's own previous product valid at the same time. SST, sea ice and snow cover stay GFS.
4. **Grid 218 products:** rebuild wgrib2 on arm64 with IPOLATES, interpolate the native B grid to
   grid 218, write `.idx` files, name files like the old NAM (`frankennam.tCCz.awphysFF.grib2`,
   not `nam.`). Zarr/Icechunk is deferred to Phase 2 (only wsis needs it).
5. **Self-chaining runners:** a runner finishes, writes its DONE, and launches the next job from
   an S3 queue file (the role gets `ec2:RunInstances` scoped to the `nam-recast` tag). This runs
   the hindcast with no laptop in the loop and is the seed of Phase 2 scheduling.
6. **Acceptance:** the Phase 0 case re-run as a tm06 product (GFS 2025-10-31 18Z → product
   2026-11-01 00Z): 29 grid-218 files with correct reference time/fh and sane PRMSL; comparison of
   tm06 vs the Phase 0 analysis-start run vs the archived NAM at f00/f24/f48/f84 (f00 is the first
   look at the 6 h information lag plus the spin-up gain); soil fields at f00 traceable to the
   archive; timing of each stage. `docs/tm06-design.md` with the results.

### B. Hindcast and scorecard (~$20, ~2 days wall, mostly waiting)
- 5 new cases + the Phase 0 case, tm06 arm on all six; analysis-start arm on 2. Candidates
  (Joe to add or swap): 2024-11-19 12Z PNW bomb cyclone + atmospheric river; 2025-01-21 00Z Gulf
  Coast snowstorm (p-type); 2025-03-14 12Z Plains severe + blizzard; one Northeast winter storm
  and one lake-effect/arctic-outbreak case from winter 2025-26; one summer MCS or quiet day.
- Verification against observations: ASOS 2 m T/Td/10 m wind (Iowa Mesonet archive), MRMS
  gauge-corrected 24 h QPE (AWS `noaa-mrms-pds`), SNOTEL precipitation (wsis fetchers), p-type by
  eye on the Gulf case. Plus the grid-to-grid stats against the archive and the GFS.
- `docs/phase1-scorecard.md`: tables by lead, 9-panels per case, the honest one-page summary.

### C. Dress rehearsal (~$3, half a day)
- An EventBridge schedule at C−2:15 (09:45Z/21:45Z) → Lambda → RunInstances launches the arm64
  runner, which waits for the GFS files, runs NPS, model, post, products, and writes a timeline.
  One live 12Z cycle, nothing published. Report every stage's clock against the old NAM's.
- Then the Phase 1 report and the Phase 2 go/no-go.

### Decisions for Joe before A starts
1. File the Spot vCPU quota raise 32 → 64 now (free; needed only if the C+3:10 f84 is not good
   enough; also lets a hindcast run overlap a test).
2. Case list: any must-have cases for the six.
3. Runner role may launch runners (self-chaining), scoped to the project tag. Recommended.
4. 3-hourly history for the hindcast (hourly measured once in C). Recommended.

### Decisions taken 4 Nov 2026 (evening) for step 2
- Spot vCPU quota raise 32 → 64 (L-34B43A08, us-west-2) **requested by Joe via CLI**; check status before B.
- Runner role may launch runners (self-chaining), scoped to the project tag: **approved**.
- 3-hourly history for the hindcast: **approved**; hourly measured once in C.
- **Filenames and prefixes duplicate the operational NAM exactly** (`nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2`
  and the same for the other product types we produce, plus `.idx`), so existing users can point
  their tooling at our bucket/URL and nothing else changes. The FrankenNAM name lives in the
  bucket/host name, the README, the index page and the honesty line, not in the file names.
- Cold-air-damming case for the hindcast: to be chosen from events where forecasters publicly
  credited the NAM (search in progress).

### Hindcast cases: CAD search result (4 Nov 2026)
Web search cannot see X posts and found no Bluesky posts crediting the NAM on a specific wedge
event. Printed credits found: Capital Weather (Nov 2026) says the NAM gave "the best
precipitation-type forecast" for the DC **"Snowcrete" storm of 5-6 Jan 2025** (snow-to-sleet
transition "almost down to the hour") and names Mid-Atlantic cold-air damming as its standout
strength; NWS Burlington's write-up of the **28-29 Dec 2025 ice storm** says observed temperatures
ended up close to the NAM3 nest, which "often captures the shallow surface cold air". The
canonical recent CAD event is the **23-25 Jan 2026 Southern ice storm** (Georgia's first ice-storm
warning in over a decade, 0.25-1 inch of ice from north Georgia to the western Carolinas).
AWS archive checked: NAM and GFS files exist for 5-6 Jan 2025 and 23-25 Jan 2026.
Proposed set (7 cases, +$2.35 over the six): Phase 0 case (2026-11-01 00Z); CAD: 2026-01-23 12Z;
p-type with a printed NAM credit: 2025-01-05 12Z (Snowcrete); Gulf Coast snow 2025-01-21 00Z;
PNW bomb cyclone 2024-11-19 12Z; Plains severe + blizzard 2025-03-14 12Z; one lake-effect/arctic
case from winter 2025-26 (agent picks from the archive and NWS write-ups).

## WOOF-NAM verification (decided 5 Nov 2026)

Joe: put WOOF-NAM beside FrankenNAM in the public validation, in two stages.

1. **Now: single case.** The GPU trial (`docs/gpu-woof-trial.md`, `deploy/10-gpu-trial.sh`) runs WOOF-NAM on the
   2026-11-01 00Z case from the GFS and keeps the history files for the table's valid times
   (f00/24/48/60/84, in `s3://nam-recast-617711905691/gpu-trial/history/`). A small reader puts their native-grid
   NetCDF (T2, U10/V10, MSLP, RAINNC+RAINC, Z500 interpolated from PH/PRES) on the same 0.25 deg CONUS-land grid as
   `run/compare.py`. That adds a WOOF-NAM column to the Validation fidelity table and a line to the RMSE-by-lead chart.
   Like the rest of that table, it is labelled as one case. The fair partner is our cold-start column (both start
   from the GFS analysis at C), unless the trial manages a tm06-style start.
2. **Later: the six hindcast cases.** One WOOF-NAM GPU run per hindcast case, same start choice as stage 1, scored
   by the same Phase 1 scorecard against the archived NAM (fidelity) and against observations (ASOS, MRMS, SNOTEL,
   p-type) next to FrankenNAM, the NAM and the GFS. Cost = six times the trial's measured $/run on one g7e.2xlarge
   (GPU quota is 8 vCPU = one such instance at a time). Budget it separately from Phase 1's $50, after the
   FrankenNAM hindcast scorecard is published.

Reporting rules: the same gate language as for FrankenNAM (fidelity to the archived NAM, GFS for context), the
WOOF-NAM commit and start configuration stated beside every number, and no "better than" framing between the
projects. Their float32 rewrite mixes code and precision differences; the page says so.
