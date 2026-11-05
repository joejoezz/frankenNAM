# FrankenNAM product plan (agreed 4 Nov 2026, evening)

FrankenNAM is **a service to the community**: forecasters lost the 12 km NAM on 3 Nov 2026 and
this project keeps its physics running, honestly labelled. Pricing covers costs and the time to
keep it running; it is not the point.

## Sequence (no money before a track record)
1. Phase 1 finishes (tm06 product configuration, hindcast scorecard, dress rehearsal).
2. Phase 2: daily 00Z/12Z cycles, the site, the free map viewer, the **live verification
   scorecard updated from every cycle**. Everything free.
3. After 2-4 weeks of live verification on the scorecard page: open subscriptions.

## Site: nam.theconvergencezone.com
- Homepage: the resurrection story; what FrankenNAM is and is not (the honesty line: initialized
  from the 6 h-earlier GFS analysis with a 6 h NAM spin-up, no data assimilation, not affiliated
  with NOAA); the delivery clock; links to code/docs.
- Live verification scorecard (per-cycle verification against ASOS/MRMS/SNOTEL + against the GFS),
  the credibility page.
- Free map viewer, same Lambda/image-loop pattern as maps.theconvergencezone.com, CONUS + the
  regional cutouts; fields: MSLP + 6 h precip, 500 Z/vort, 700 RH/omega, 850 T/wind, 2 m T/Td,
  10 m wind, simulated reflectivity, p-type, 6 h and run-total precip, snowfall (10:1 and Kuchera),
  CAPE/CIN, PWAT, soundings page (BUFKIT).
- Subscribe page with swap-in instructions (wgrib2, Herbie, BUFKIT) and status.

## Paid tier: the grids (and BUFKIT files)
- **Monthly only, $14.99/month, cancel any time.** No annual plan: a prepaid year is a promise to
  run the service for a year, and with few subscribers that promise could be impossible to keep.
  Monthly keeps the obligation to one billing period; the terms say the service can be wound down
  with a month's notice and no further charges.
- **Founding members: the first 15 paying subscribers.** The promise: once the paying-subscriber
  pledge is filled (**20 paying subscribers**, decided 4 Nov 2026), founders drop to
  **$9.99/month** and stay there for as long as their subscription remains active. Stripe handles
  this as a price swap on their subscription. The counter is public on the subscribe page.
- **Comped access (NWS offices, educators): only once a baseline of paying subscribers subsidises
  it.** Rule: no comps until the pledge (20) is filled; then at most one comp per five
  paying subscribers, reviewed every six months, revocable if the paying base shrinks. Comped keys
  are ordinary keys with the same fair-use expectations.
- Stripe Checkout + customer portal; webhook toggles the subscriber key.
- Access = key in the URL path, validated by a CloudFront Function/Worker and stripped before the
  origin, so every existing tool works unchanged:
  `https://grids.theconvergencezone.com/<key>/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2`
- **Files served from Cloudflare R2** (S3 API, zero egress): AWS→R2 copy once per cycle
  (~2-3 GB, ~$13/month of AWS egress for 60 cycles). This removes the per-subscriber egress ceiling
  that would otherwise eat a $10-15 plan (a full-pull user ≈ 108 GB/month ≈ $9 on CloudFront).
- File names and prefixes identical to the operational NAM (decided earlier).
- Break-even ≈ 12-15 subscribers at $14.99 against ~$200/month of compute + transfer; at the
  20-subscriber pledge with 15 founders at $9.99, revenue ≈ $225/month, roughly costs.
- Operator: **Joe Boomgard-Zagrodnik, sole proprietorship (California)**, decided 5 Nov 2026; Stripe,
  terms, LICENSE/NOTICE copyright and the contact all name Joe personally (no LLC for now).

## Transparency: publish what it costs
The site carries a running cost page: compute per cycle and per month, transfer, storage, the
subscriber count against the pledge, and the **startup cost of the resurrection** (Phase 0 ≈ $10.6,
Graviton port ≈ $9.4, Phase 1 target < $50, plus the engineering time, stated honestly). Updated
from the AWS cost allocation tag `project=nam-recast` and the Stripe subscriber count.

## Name
FrankenNAM stays for now (Joe, 5 Nov 2026). Logged alternative: **OpenNAM** (simple, searchable;
honest only if the repo is public at launch so "open" means open code + open verification + open
costs, with paid grids covering hosting). Also considered: NAMcast, NAM Continuity, NAM12.
All were unregistered in .com/.org on 5 Nov 2026 (rough whois). A rename touches the repo name,
products README, site copy and memory, nothing shipped yet; half an hour when decided.

## Not yet decided
- Whether the maps stay fully free forever (recommended: yes, they are the funnel and the
  community service) and whether BUFKIT files sit in the free or paid tier.
- Region of the R2 bucket, custom domain for grids, status/alerting page.
- The comp ratio (1 per 5 proposed).
