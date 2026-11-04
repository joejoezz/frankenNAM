# Phase 1 hindcast cases and staged inputs (4 Nov 2026)

Seven cases: the Phase 0 case (staged by the other brief, untouched) and six new ones. C is the product cycle
(the archived NAM's init time); P = C - 6 h is the GFS cycle a tm06 FrankenNAM starts from.
All inputs are server-side copies from the public buckets into `s3://nam-recast-617711905691/cases/<C>/`
(us-west-2); nothing was substituted: every requested cycle was complete in both archives.

| C | P | Event | Staged (GB) | Arms |
|---|---|---|---|---|
| 2026-11-01 00Z (`2026110100`) | 2025-10-31 18Z | Phase 0 case (autumn, CONUS-wide) | not touched | by brief A |
| 2026-01-23 12Z (`2026012312`) | 2026-01-23 06Z | CAD ice storm, GA/Carolinas (23-25 Jan 2026; Georgia's first ice-storm warning in over a decade) | 34.1 | tm06 + analysis-start reference |
| 2025-01-05 12Z (`2025010512`) | 2025-01-05 06Z | "Snowcrete", DC, 5-6 Jan 2025 (snow to sleet; Capital Weather credited the NAM with the best p-type forecast) | 34.3 | tm06 + analysis-start reference |
| 2025-01-21 00Z (`2025012100`) | 2025-01-20 18Z | Gulf Coast snow, 21-22 Jan 2025 (rare snow, p-type) | 18.5 | tm06 |
| 2024-11-19 12Z (`2024111912`) | 2024-11-19 06Z | PNW bomb cyclone + atmospheric river | 18.5 | tm06 |
| 2025-03-14 12Z (`2025031412`) | 2025-03-14 06Z | Plains severe weather + blizzard, 14-16 Mar 2025 | 18.5 | tm06 |
| 2025-12-29 12Z (`2025122912`) | 2025-12-29 06Z | Lake-effect / arctic outbreak, Great Lakes, 29 Dec 2025 - 2 Jan 2026 | 18.6 | tm06 |

Total staged: 142.0 GB in 1,016 objects (data + `.idx`). S3 transfer at about 0.02 USD/GB inter-region: about 2.84 USD,
plus requests of a few cents; storage 142 GB is about 3.3 USD per month while it stays. The data stays until the hindcast is done.

## Layout under `cases/<C>/` (same naming as the Phase 0 case)
- `gfs-tm06/gfs.tPPz.pgrb2.0p25.fFFF` + `.idx`: P-cycle GFS f000-f090 every 3 h (31 files, `pgrb2.0p25` only).
- `nam-archive/nam.tCCz.awphysFF.tm00.grib2` + `.idx`, FF = 00..84 every 3 h (29 files), plus
  `nam.tPPz.awphys00.tm00.grib2` of the P cycle (the soil seed; its name does not clash).
- `gfs/gfs.tCCz.pgrb2.0p25.fFFF` + `.idx`, f000-f084 every 3 h: only for the two analysis-start reference cases (CAD, Snowcrete).
- `MANIFEST.txt`: object (relative key) and size in bytes, tab separated.
Staging script: `verify/stage_case.py` (`stage_case.py YYYYMMDDHH [--ref-arm] [--check-only]`; it checks every object exists before copying).

## Data checks (all passed before staging)
For each C: `noaa-nam-pds` has `nam.tCCz.awphysFF.tm00.grib2` for FF = 00..84 step 3 and the P-cycle `awphys00`;
`noaa-gfs-bdp-pds` has the P-cycle `pgrb2.0p25` f000-f090; for the two reference cases also the C-cycle f000-f084.
0 of 180 (reference cases) or 0 of 122 (others) objects were missing. For the observation side: IEM ASOS covers every window;
MRMS `MultiSensor_QPE_24H_Pass2` hourly files exist for every needed end time on all dates (checked 2024-11-20, 2025-01-06,
2025-01-22, 2025-03-15, 2026-01-24); SNOTEL hourly PREC is available for the PNW and Plains cases.

## Why the winter 2025-26 lake-effect case is 2025-12-29 12Z
Candidates in winter 2025-26: the late-Nov/early-Dec lake-effect spell after Thanksgiving, and the 28 Dec 2025 - 1 Jan 2026
event. The second is the better test: a Dec 28-30 winter storm with blizzard conditions crossed the region (Midwestern
Regional Climate Center, Great Lakes winter 2026 summary), then arctic air produced a multi-day lake-effect outbreak: Fox Weather
reported Syracuse at 2 feet on Tuesday 30 Dec (its second-snowiest day on record), State of Emergency expanded in New
York, and Winter Storm / Lake Effect Snow Warnings around Syracuse, Buffalo and Erie, PA into New Year's Day. NWS Burlington's
write-up of the 28-29 Dec ice storm (see the CAD search in `phase1-plan.md`) also credits the NAM3 nest with the shallow cold
air in that stretch. A 12Z cycle on 29 Dec covers the cold-air arrival and the peak of the Dec 30 band through 2 Jan 00Z. The
evidence is news and climate-summary level; no NWS event pages were read, and the web search could not see social media.
Caveat to remember in the reading: lake-effect bands are far below the 12 km grid scale, so skill here is mostly about the
air-mass and wind-direction forecast, not band placement.

## Observation sets per case
ASOS/AWOS hourly (all cases), MRMS 24 h QPE (all cases), SNOTEL 24 h precipitation (PNW and Plains cases), ASOS present-weather
p-type (CAD, Snowcrete, Gulf). See `verify/` and `docs/baseline-scorecard.md`.
