## Reading (short, honest)

Seven cases, 12-84 h, all against observations: ASOS/AWOS stations (about 390,000 station-hours per variable), MRMS 24 h QPE
(Pass2, gauge-corrected) and SNOTEL. These are cases picked for weather, not a random sample, and the seven are not independent
samples of anything. No significance tests; differences of a few hundredths of a K or m/s are noise.

**Where the old NAM beat the GFS against observations**
- 2 m dew point: lower bias (+0.06 K against -0.34 K, the GFS is too dry everywhere) and a clearly better first day (3-24 h RMSE
  2.67 vs 2.84 K); from 27 h the two are tied (3.06 vs 3.07 K over 12-84 h).
- 2 m temperature: NAM bias is about zero (+0.05 K), GFS runs warm (+0.34 K; +0.8 K in the West, +0.7 K on the Plains). That does
  not turn into a lower RMSE overall, except beyond 51 h (2.89 vs 2.91 K) and in three cases:
  Snowcrete (2.39 vs 2.63 K), the late-December lake-effect case (2.79 vs 2.96 K) and, marginally, the CAD case (3.00 vs 3.03 K).
- 10 m wind: no difference (2.13 vs 2.12 m/s); both are about 0.5 m/s too fast on average. In the Plains the NAM has no bias
  (-0.01 vs +0.45 m/s).
- SNOTEL, PNW atmospheric river: the NAM puts more precipitation in the mountains (ratio 0.87 vs the GFS's 0.71 of observed), but it
  correlates slightly worse (0.69 vs 0.72) and has a larger MAE.

**Where it did not**
- 24 h precipitation against MRMS: the GFS has a higher ETS at all three thresholds (2.5/10/25 mm: 0.567/0.545/0.391 vs
  0.536/0.496/0.353) and a lower MAE (1.58 vs 1.76 mm per day). The NAM is ahead only in some case/threshold cells (CAD at 2.5 and 25 mm, Snowcrete at 10 mm, Gulf snow at 25 mm,
  lake-effect at 2.5 and 10 mm) and behind in the rest, most clearly in the PNW case (25 mm: 0.39 vs 0.54). Frequency bias is fine for both (about 1.0-1.1).
- 2 m temperature RMSE is a tie overall (2.72 vs 2.72 K) and the GFS is better in the first two days (3-48 h) and in the NE
  (2.40 vs 2.77 K) and on the Phase 0 and Plains cases (2.33 vs 2.50 K, 2.47 vs 2.74 K).
- Precipitation type: the NAM's printed credit (Snowcrete) is not reproduced by hourly ASOS present weather. In the Snowcrete
  event region the NAM and the GFS agree with the observed type about equally (76% vs 80% at 3-36 h, 52% vs 50% at 39-84 h). In
  the CAD event region the NAM matched observed type in 25% of the early hours against 52% for the GFS (123 hours only; the NAM
  turned many observed snow hours into sleet and freezing rain), and for the Gulf snow the NAM scored 45% against 78%
  (it often had no precipitation-type flag at all where snow was reported). The NAM only leads in CONUS-wide agreement at
  39-84 h. These are station-hour counts with strong serial and spatial correlation, and the categorical flags are only a slice of
  how forecasters use the NAM (soundings, the NAM nest), so this is a limit on what the awphys flags can claim, not on the model.
- The Phase 0 result "the recast is closer to the NAM than the GFS is" does not say much about skill: on the Phase 0 case the archived
  NAM was worse than the GFS against stations for 2 m temperature (2.50 vs 2.33 K) and against MRMS for precipitation.

**What this sets as the bar for FrankenNAM (12-84 h, pooled, CONUS)**
T2m RMSE 2.72 K (NAM) / 2.72 (GFS) / 2.77 (6 h older GFS); Td 3.06 / 3.07 / 3.12 K; wind 2.13 / 2.12 / 2.13 m/s; precipitation
ETS at 2.5 / 10 / 25 mm: 0.536 / 0.496 / 0.353 (NAM), 0.567 / 0.545 / 0.391 (GFS), 0.553 / 0.525 / 0.374 (older GFS).
The Phase 1 gate, "beat the GFS against observations", is therefore demanding on precipitation (the same-cycle GFS is better than
the NAM it imitates) and nearly free on T and wind, where the GFS and NAM are tied. The 6 h older GFS (the information a tm06
FrankenNAM starts from) is slightly worse than the same-cycle GFS everywhere (T2m +0.05 K, Td +0.06 K, ETS -0.01 to -0.02), so the lag
costs little; the like-for-like comparator for a tm06 product is the older GFS column.

**Method caveats:** temperatures use a lapse-rate correction and a 400 m terrain filter, so mountain stations are only partly
represented; MRMS under-catches snow and precipitation in the mountain West, and Pass2 gauge correction there is thin; SNOTEL
values are coarse (0.1 in per gauge reading) and not terrain-adjusted; precipitation boxes use bilinear (GFS) vs box-mean
(NAM) sampling.
