# Brief A: the FrankenNAM product configuration (tm06 spin-up, soil seeding, NAM-identical products)

Read first: `docs/phase1-plan.md` (sections "Next: Phase 1 step 2", "Decisions taken 4 Nov 2026
(evening)", "Hindcast cases"), `docs/scoping.md` ("Decisions after Phase 0"), `docs/graviton-port.md`,
`docs/run-notes.md`, `run/README.md`. Everything runs on **arm64** (c8g.8xlarge Spot, restarts off,
`deploy/04-run-case.sh ARCH=arm64`, arm build box via `deploy/05-graviton-box.sh` / `deploy/06-stop-arm.sh`).
The x86 box `i-0ab3bbee9ba7068e7` stays stopped and untouched. Do not run `deploy/01-build-box.sh`
(it starts the x86 box).

## What the product is
A FrankenNAM cycle C (00Z or 12Z) is a 90 h NMMB integration started at **P = C − 6 h from the GFS
cycle P**: `gfs.tPPz.pgrb2.0p25.f000` is the initial condition, `f003 … f090` are the 3-hourly
boundaries. Integration hour 6 is product **f00**; hour 90 is f84. There is no data assimilation;
the 6 h of NAM physics before f00 replace the operational 6 h catch-up. Products carry reference
time C and forecast hours 0-84, and the honesty line: *"Initialized from the PPZ GFS analysis with a
6 h NAM spin-up. No observations after PPZ."*

## Deliverables
1. **`run/recast.sh` tm06 mode** (`MODE=tm06`, default from now on; the Phase 0 analysis-start mode
   stays available as `MODE=anl` for the reference arm): stage the P-cycle GFS from
   `noaa-gfs-bdp-pds` (server-side copy into `s3://nam-recast-617711905691/cases/<C>/gfs-tm06/`),
   NPS as in Phase 0, 90 h integration, **3-hourly history, 3 h precipitation buckets**, TDFI at
   start, `NO_RESTART=1`, history kept on the node only (no S3 sync of history), UPP on hours 6-90.
2. **Soil seeding/cycling through metgrid:** a second ungrib source (its own Vtable + prefix) carrying
   the four Noah layers (0-10/10-40/40-100/100-200 cm soil moisture and temperature), snow depth and
   water equivalent, canopy water and skin temperature, read from a **grid-218 NAM-format GRIB2 file
   valid at P**: in hindcasts the archived `nam.tPPz.awphys00.tm00.grib2`, live our own previous
   product valid at P. metgrid must prefer that source for those fields over the GFS (verify how
   NPS's metgrid resolves duplicate fields across `fg_name` sources in its source; document it).
   SST, sea ice and snow cover stay GFS. Acceptance: f00 soil moisture/temperature in the product
   trace to the seed (plot/compare against the seed file), not to the GFS.
3. **Products identical in form to the operational NAM** (`run/products.sh`):
   - Rebuild `wgrib2` on arm64 **with IPOLATES** (NCEPLIBS-ip/sp are already built) so `-new_grid`
     works on the rotated B grid; interpolate to **grid 218** (Lambert conformal, 614x428, 12.19 km;
     take the exact grid definition and the wind-rotation convention from an archived `awphys` file
     with `wgrib2 -grid -vector`). 
   - Match the archived file's **inventory** (`wgrib2 -s` of `nam.t00z.awphys24.tm00.grib2` from the
     case's `nam-archive/`) record for record as far as our fields allow: same variables, levels,
     and the same APCP/accumulation bucket structure (inspect what the 00Z/12Z awphys files carry
     and rebuild it from our 3 h buckets with `wgrib2 -rpn`/`-set_ftime`). Document every record we
     cannot produce and why.
   - Rewrite reference time to C and forecast hour to h−6 (`wgrib2 -set_date` / `-set_ftime`).
   - **File names and prefixes duplicate the NAM exactly:** `nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2`
     plus `.idx` in the NOMADS format (`wgrib2 -s`), under `s3://nam-recast-617711905691/products/`.
     The FrankenNAM name goes in a `README.md` at the products root (with the honesty line), never
     in the file names. A user must be able to swap our URL for NOMADS and change nothing else.
   - Post must overlap the integration (as UPP already does); products for f00…f84 should be
     complete within ~10 min of the model finishing. Record the clock of every stage.
4. **Self-chaining runners:** `deploy/07-runner-policy.sh` adds to the `nam-recast-ec2` role
   `ec2:RunInstances`, `ec2:CreateTags`, `ec2:DescribeInstances/Images/Subnets/SecurityGroups`,
   `ec2:TerminateInstances` and `iam:PassRole` for itself, scoped to `project=nam-recast` tags where
   the action supports a tag condition (Joe approved this). A runner, when its job is done, pops the
   next line (`CYCLE MODE ARCH`) from `s3://nam-recast-617711905691/queue/hindcast.txt` (atomic
   enough: read, rewrite, then launch) and launches the next runner with the same user-data. Test it
   with a two-line queue of short runs before relying on it.
5. **Acceptance run:** the Phase 0 case as a tm06 product: P = GFS 2025-10-31 18Z, C = 2026-11-01 00Z,
   soil seeded from the archived `nam.t18z.awphys00.tm00.grib2` of 2025-10-31 (stage it). Deliver
   29 grid-218 files with correct reference time/forecast hours and sane PRMSL, and
   `run/compare.py` extended so the comparison table has **tm06 | arm anl (Phase 0 arm64 run) | archived
   NAM | GFS** at f00/f24/f48/f84 for the Phase 0 fields plus 24 h precipitation. f00 is the first
   measurement of the 6 h information lag against the spin-up gain; report it plainly either way.
6. **`docs/tm06-design.md`:** the design as built, the metgrid precedence finding, the inventory
   match table (ours vs archive, record by record), the acceptance comparison, the stage clock and
   the projected live clock for a 12Z cycle on one c8g.8xlarge (GFS P-cycle lands ~C−2:00), what
   broke, cost. Update `run/README.md`.

## Rules
- Budget **$10** for this brief (arm box on-demand $1.28/h: stop it whenever you wait more than
  ~20 min; Spot runners $0.47/h; cross-region GFS copies ~$0.30 per case). Report spend.
- Short tests first (6-12 h integrations), the full 90 h acceptance run once.
- Terminate every runner you launch; leave no open Spot requests; stop the arm box at the end.
- Touch nothing outside this repo, the `nam-recast-617711905691` bucket and `nam-recast*`
  instances; never the x86 box; never other projects. No user-agent spoofing or access-control
  workarounds. Commit small with named paths (no `git add -A`), author is Joe (configured), end
  commit messages with the Co-Authored-By line set for this session.
- If something in the design cannot work as written (e.g. metgrid cannot prefer the second source,
  or the APCP structure cannot be rebuilt), do not silently substitute: implement the closest
  honest alternative, mark it clearly in the doc, and say so in the report.
