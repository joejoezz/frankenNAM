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
- **$14.99/month**, **introductory $120/year** (founding rate; recommend locking it for as long as
  the subscription stays active, as the ENSO app did with its founding cutoff).
- Stripe Checkout + customer portal; webhook toggles the subscriber key.
- Access = key in the URL path, validated by a CloudFront Function/Worker and stripped before the
  origin, so every existing tool works unchanged:
  `https://grids.theconvergencezone.com/<key>/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2`
- **Files served from Cloudflare R2** (S3 API, zero egress): AWS→R2 copy once per cycle
  (~2-3 GB, ~$13/month of AWS egress for 60 cycles). This removes the per-subscriber egress ceiling
  that would otherwise eat a $10-15 plan (a full-pull user ≈ 108 GB/month ≈ $9 on CloudFront).
- File names and prefixes identical to the operational NAM (decided earlier).
- Break-even ≈ 12-15 subscribers at $14.99 against ~$200/month of compute + transfer.
- Subscriptions run through the LLC. Free/comped access for NWS offices and educators is Joe's
  call later.

## Not yet decided
- Whether the maps stay fully free forever (recommended: yes, they are the funnel and the
  community service) and whether BUFKIT files sit in the free or paid tier.
- Region of the R2 bucket, custom domain for grids, status/alerting page.
