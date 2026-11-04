# FrankenNAM products

These files are **FrankenNAM**, a community recast of the retired NOAA/NCEP North American
Mesoscale model (NAM, 12 km NMMB core, NAM v4.2 physics), run on AWS from the NAM's own source
code. They are **not** produced by NOAA.

**Initialized from the (C−6)Z GFS analysis with a 6 h NAM spin-up. No observations after (C−6)Z.**
A cycle labelled 00Z starts at 18Z the previous day from the 18Z GFS analysis (12Z cycles from the
06Z GFS), integrates 6 h of NAM physics to the cycle time, which is f00, and continues to f84 with
GFS lateral boundaries. There is no data assimilation; the Noah land state is carried from the
previous FrankenNAM cycle (hindcasts: from the archived NAM valid at the start time).

## Layout

Names and prefixes duplicate the operational NAM so existing tooling can point here and change
nothing else:

```
nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2        grid 218 (Lambert conformal, 614 x 428, 12.19 km), FF = 00..84 by 3
nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2.idx    wgrib2 -s inventory, NOMADS format
```

Content: the same variables, levels and accumulation structure as the operational `awphys`
files (12 h precipitation buckets on the cycle clock plus 3 h APCP/ACPCP after the first hour of
each bucket, 1 h max/min 2 m T/RH and 10 m wind, instantaneous fluxes and cloud cover), interpolated
with the same wgrib2 recipe as the operational product generator (bilinear; nearest neighbour for
categorical and soil fields; budget for accumulations; grid-relative winds). Differences from the
NAM that users should know about are listed in `docs/tm06-design.md` of the nam-recast repository.
Products are cycled at 00Z and 12Z only.

Reference time in every record is the cycle time C; the forecast hour counts from C.
