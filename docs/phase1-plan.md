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

**Gate to Phase 2 (all three):**
1. On the hindcast set, the tm06 FrankenNAM beats the GFS against **observations** at 12-84 h on
   2 m T, 10 m wind and 6 h/24 h precipitation over CONUS, and tracks the archived NAM at least
   as closely as in Phase 0.
2. One real-time dress-rehearsal cycle delivers f84 within 3 h of cycle time.
3. Products (GRIB2 on the familiar grid 218 + Zarr) open in standard tools and verify as sane.

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
