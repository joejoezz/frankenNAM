# site/: FrankenNAM maps, viewer and pages (nothing deployed)

```
site/render/    grid-218 awphys GRIB2 -> PNG frames (Python)
site/viewer/    static image-loop viewer (one HTML file, plain JS)
site/pages/     homepage, scorecard, costs, subscribe, terms (plain HTML/CSS)
site/gen/       generators: grid status/index pages, scorecard page, cost page (+ Cost Explorer stub)
site/products/  README for the grid host
site/samples/   a handful of rendered PNGs and viewer screenshots
```

Everything here was developed against the archived operational NAM (`s3://noaa-nam-pds`), whose grid-218
`awphys` files have the same form, names and `.idx` layout as FrankenNAM's. No AWS, DNS or Cloudflare
resource was created for this.

## Render a cycle and look at it

```
python3 -m venv ~/data/nam-recast-site/venv && ~/data/nam-recast-site/venv/bin/pip install -r site/requirements.txt

# sample data: 2026-11-01 00Z, f00-f84 every 3 h (29 files + .idx, ~1.8 GB, free)
mkdir -p ~/data/nam-recast-site/nam.20261101
aws s3 sync --no-sign-request --region us-east-1 s3://noaa-nam-pds/nam.20261101/ \
    ~/data/nam-recast-site/nam.20261101/ --exclude "*" --include "nam.t00z.awphys??.tm00.grib2*"
# (the bucket holds every forecast hour; the render only needs 3-hourly: delete the rest or use --fhrs)

python site/render --cycle 2026110100 --src ~/data/nam-recast-site/nam.20261101 --out /tmp/x
python site/render ... --regions conus,northeast      # or --regions all
python site/render ... --fields t2m,snowku --fhrs 0:84:6
open /tmp/x/index.html                                # works from file://
```

`python -m site.render` (as the brief wrote it) cannot work: `site` is a standard-library module that Python
has imported before it looks at the current directory. Run the package by path (`python site/render ...`)
or as `cd site && python -m render ...`.

`--product nam|frankennam` chooses the footer each PNG carries (the archive sample says it is not
FrankenNAM; the FrankenNAM one carries the honesty line). `--model` is the folder name under `frames/`.

### What it renders

15 fields: MSLP + 6 h precip, 500 hPa height + absolute vorticity, 700 hPa RH + omega, 850 hPa T + wind,
2 m T, 2 m Td, 10 m wind, simulated composite reflectivity, p-type, 6 h precip, run-total precip, snowfall
(10:1 and Kuchera), CAPE/CIN, PWAT. Regions (`site/render/regions.py`): CONUS, northwest, southwest,
rockies, central, southeast, northeast. Accumulation fields have no f00 frame.

- Run totals are built from the NAM's accumulation buckets (0-3, 0-6, 0-9, 0-12, then 12-15 ... 24-27 ...
  with 12 h buckets restarting); `render/acc.py` parses the bucket from each file's `.idx`, so it does not
  depend on that layout.
- Kuchera: the 3-hourly step of the model's liquid-equivalent snow (WEASD) times the Kuchera ratio, taken as
  the mean of the ratios at the step's ends, from the warmest of 2 m and 1000/925/850/700/600/500 hPa
  temperature above ground (the ensplots rule, `ensplots/maps.py`).
- Only the needed GRIB messages are read, by byte range from the `.idx` (about 60 per forecast hour), from a
  local directory or an `https://` prefix, so a Lambda never downloads a 60 MB file.
- Output PNGs are 256-colour palette images (~140 KB each; 3x smaller than RGB, same look).

### Timing (laptop, 8 cores; 2026-11-01 00Z, all 15 fields, 29 hours)

| | frames | wall |
|---|---|---|
| CONUS, 8 processes | 431 | 27 s |
| CONUS + northeast, 8 processes | 862 | 61 s |
| CONUS, 1 process | 431 | 93 s |

The cycle totals (precip, snow) are computed first, in order, in about 1 s.

### Naming scheme (same family as ensplots)

ensplots writes `frames/<model>/<YYYYMMDDHH>/<NNN>[-<fill>].{json,bin}` plus `maps/runs.json`. Here:

```
runs.json, runs.js                                  cycles on offer, per model
frames/<model>/<YYYYMMDDHH>/index.json, index.js    fields, hours, regions, "?" text per field
frames/<model>/<YYYYMMDDHH>/<region>/<fff>-<field>.png
```

`model` is `nam` (the archived sample) or `frankennam`. The `.js` twins hold the same JSON assigned to a
`window` variable; the viewer loads those with `<script>` because browsers block `fetch()` of local JSON
under `file://`.

## The viewer

`site/viewer/index.html`: cycle and region selectors, a tab per field, forecast-hour scrubber with play,
previous, next and a speed control, preloading of the loop, a "?" box per field (text comes from
`index.json`, so it lives next to the field definition in `render/fields.py`), and a notice banner when the
shown model is the archive. Keys: left/right step, space play, up/down field, `[` `]` region, Home/End, `?`
help. The URL hash keeps the state (`#nam/2026110100/conus/snowku/72`).

Every URL is relative to a data root (the page's own folder; override with `?data=` or the
`data-root` meta tag), so the same page works from a local folder, from an S3/R2/CloudFront prefix and from
a sub-path such as `/maps/`. It is not MapLibre: ensplots' viewer pans and zooms vector layers over one
North America domain; the brief asked for rendered PNGs, so this is an image loop. Pan/zoom comes from
the regional cutouts, not from the viewer.

## The pages

`site/pages/`: `index.html` (story, the honesty line, what it is and is not, delivery clock),
`scorecard.html` (skeleton; every cell is a dash until `verify/` feeds it), `costs.html` (running and
startup costs, pledge counter), `subscribe.html` (monthly $14.99, founding 15 to $9.99 at 20 paying,
key-in-URL, wgrib2 / Python / Herbie / BUFKIT swap-in), `terms.html`. Yellow boxes marked
`[PLACEHOLDER ...]` or `[DECISION NEEDED ...]` are items that need a number, a decision or a tested snippet.
No skill or verification claim appears anywhere. Layout when assembled: pages at the root, the viewer and
its frames under `maps/`:

```
mkdir -p /tmp/y/maps && cp site/pages/* /tmp/y/ && python site/render ... --out /tmp/y/maps
```

## FrankenNAM and the archived NAM together (compare mode)

Render both into one folder, each under its own `--model`; the viewer lists both and offers a "compare" selector
(models that share the cycle). Side by side or flip between the two with synced scrubbing; keys `c` (compare on/off)
and `x` (flip). The hash keeps it (`#frankennam/2026110100/conus/snowku/72/nam`).

```
aws s3 sync --region us-west-2 s3://nam-recast-617711905691/products/nam.20261101/ ~/data/nam-recast-site/frank/nam.20261101/
python site/render --cycle 2026110100 --src ~/data/nam-recast-site/frank/nam.20261101 --out OUT --model frankennam --product frankennam --regions conus,northeast
python site/render --cycle 2026110100 --src ~/data/nam-recast-site/nam.20261101       --out OUT --model nam --product nam --regions conus,northeast
```

Measured: FrankenNAM 862 frames (15 fields, 29 hours, CONUS + northeast) in 44 s, the archive in 43 s, 8 processes.
The FrankenNAM footer names the analysis it starts from (the cycle minus 6 h), computed from the cycle.

## Generators (`site/gen/`, standard library only)

- `grid_index.py --src <dir or s3://prefix> --out DIR [--now ISO]`: `status.json`, a root `index.html` (cycles, newest
  first, 7-day window), `nam.YYYYMMDD/index.html` (every GRIB2/.idx with size and SHA-256) and `nam.tCCz.cycle.json`.
  States: complete (29 hours with GRIB2 and .idx), running, incomplete (no file for `--stale-minutes`). S3 is read
  through the aws CLI; hashes are cached in `sha256.json`, so reruns hash only new files (58 files, 1.8 GB: about 1 s of
  hashing on the laptop, 0.03 s on rerun). Tested on a complete cycle, a partial cycle and an empty window.
- `scorecard.py [--results DIR ...] [--out FILE]`: the scorecard page from `verify/results/*/` sums. Baseline columns
  now (NAM, GFS, 6 h older GFS); an empty FrankenNAM column that fills when `fnam` rows exist in any results dir
  (and then every column is restricted to the cases `fnam` has). A "fidelity to the archived NAM" table applies the
  Phase 1 margins. Numbers reproduce `docs/baseline-scorecard.md`.
- `costs.py [--data costs.json] [--out FILE]`: the cost page from `costs.json`; `costs_from_aws.py` is a stub that
  would fill the JSON from Cost Explorer by the `project=nam-recast` tag. It has not been run.

Pages are regenerated into `site/pages/`; do not edit `scorecard.html` or `costs.html` by hand.

## Deployment plan (document only; nothing deployed)

Target host `nam.theconvergencezone.com` for pages and maps; `grids.theconvergencezone.com` for grids.

### Maps and pages: AWS, the ensplots pattern

| ensplots (maps.theconvergencezone.com) | FrankenNAM maps |
|---|---|
| Lambda container image (arm64, ECR), `deploy/02`, `03` | same image recipe with `site/requirements.txt`; entry point calls `render.render_frame(cycle, field, region, fhr, src, out)` |
| EventBridge hourly poll for new ECMWF runs (`deploy/04`) | no poll: the run job's last step per hour (or an S3 event on the `.idx`, written after the GRIB) puts `(cycle, fhr)` on SQS; one Lambda per hour renders all fields and regions for that hour |
| Fan-out to worker invocations of the same function | the per-hour message is the fan-out; the cycle totals are cached as `_work/<cycle>/cum_fNNN.npz` and read by later hours |
| `maps/runs.json` plus page rewritten each pass | `runs.json`/`runs.js` and `index.json`/`index.js` written when the last hour lands |
| Public S3 bucket + CloudFront, 7-day lifecycle (`deploy/06`) | public bucket `frankennam-public-<acct>` + CloudFront, `frames/` expires after 7 days (14 cycles), pages and viewer permanent |
| Domain: ACM cert in us-east-1, CNAME pasted at WordPress.com (`deploy/09`) | same: cert for `nam.theconvergencezone.com`, CNAME by hand |
| Alarm on missed passes, SNS `wsis-alerts` (`deploy/07`) | alarm when a cycle's index is not complete N minutes after the model's last file |
| Region eu-central-1 (ECMWF mirror lives there) | us-west-2, beside the model run output and the rest of the account |

Cost, maps (estimates; render times measured on the laptop):
- Lambda: about 82 CPU-seconds per CONUS cycle measured on the laptop (93 s wall on one process), so
  about 3 s of work per hour on a 3 GB arm64 function: well under $0.01 per cycle for CONUS, roughly $0.03-0.05 for all seven
  regions (about $2-3 a month at 60 cycles).
- S3: about 59 MB per cycle for CONUS and about 48 MB per regional cutout; seven regions is about 350 MB
  a cycle, so a 7-day roll-off (14 cycles) holds about 5 GB: pennies a month.
- CloudFront: one field loop is about 4 MB (29 frames), so 1,000 loops a day is about 120 GB a month, inside
  CloudFront's free 1 TB a month if the account's free tier applies (check; otherwise about $10).
- Total for maps: single-digit dollars a month.

### Grids and key validation: Cloudflare R2 + Worker

Per the product plan: the run job copies each cycle's GRIB2 and `.idx` (about 2-3 GB) from AWS to an R2
bucket; a Worker validates `<key>` in the path against Workers KV, strips it, and streams the object from
R2 through a bucket binding. Stripe's webhook (a second Worker route) writes and clears KV entries.

| Item | Estimate |
|---|---|
| AWS to R2 copy, 60 cycles a month at 2-3 GB, $0.09 per GB egress | about $13 a month (the plan's figure) |
| R2 storage, 30-day archive (about 150 GB at $0.015 per GB-month) | about $2-3 a month |
| R2 reads (byte-range GETs are Class B; $0.36 per million) and egress | egress is free; a heavy user is a few thousand requests a day, cents |
| Workers (paid plan $5 a month covers 10 million requests) and KV | $5 a month |
| For comparison, CloudFront + S3 for grids at $0.085 per GB | a user pulling every file (about 108 GB a month) costs about $9, which is why the plan chose R2 |

Total, grids: about $20 a month before payment fees, to set against compute.

Order of work when deployment is approved: bucket + CloudFront + cert and DNS (pages and viewer, nothing
else), then the Lambda and queue, then the alarm, then R2, the Worker and Stripe.

### Open questions for Joe

1. **DNS for the grid host.** theconvergencezone.com DNS is at WordPress.com. Cloudflare Workers routes and
   R2 custom domains need the zone on Cloudflare (or a paid subdomain-delegation setup). Options: move the
   zone to Cloudflare; give the grids a domain that is on Cloudflare (for example a frankennam domain,
   which the scoping doc noted looked unregistered); or serve grids from CloudFront with a CloudFront
   Function key check and accept the egress cost.
2. **Regions.** maps.theconvergencezone.com has one North America domain, not regional cutouts, so the
   seven regions here are a proposal. Are they the right set?
3. **Maps free forever** (recommended in the plan, still listed as undecided), and whether BUFKIT files are
   free or paid: the subscribe page has a placeholder for it.
4. **Refund policy, fair-use limit, log retention, LLC name and contact:** placeholders in `terms.html`.
5. **Pan/zoom.** The viewer is an image loop. A MapLibre viewer with GPU-colored fills, like ensplots, would
   need the fields as value grids (`.bin`) instead of PNGs. It is a larger piece of work; say if you want it.
