# FrankenNAM grids

These files are **FrankenNAM**, a community recast of the retired NOAA/NCEP North American Mesoscale
model (NAM, 12 km NMMB core, NAM v4.2 physics), run on cloud computers from the NAM's own source code.
They are **not produced by NOAA** and are not affiliated with or endorsed by NOAA.

> **Initialized from the (C-6)Z GFS analysis with a 6 h NAM spin-up. No observations after (C-6)Z.**

C is the cycle time. A cycle labelled 12Z starts at 06Z from the 06Z GFS analysis, runs 6 h of NAM physics
to 12Z (that is forecast hour 0 of the product) and continues to f84 on GFS lateral boundaries. The 00Z
cycle starts from the 18Z analysis. There is no data assimilation, so the first hours differ most from the
operational NAM. Only the 12 km parent domain is run: no 3 km nests, no Alaska, Hawaii or Puerto Rico.

## What the files are

One GRIB2 file and one `.idx` per forecast hour, on grid 218 (Lambert conformal, 614 x 428, 12.19 km),
f00 to f84 every 3 h, for the 00Z and 12Z cycles. About 454 records per forecast hour (446 at f00), the same variables, levels
and accumulation structure as the operational `awphys` files.

### The names are NOAA-identical on purpose

```
nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2        FF = 00, 03, ... 84
nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2.idx    wgrib2 -s inventory, NOMADS format
```

so that scripts written for NOMADS, AWS Open Data or the NAM mirrors work with only the base URL
changed. The name is the only thing the files share with NOAA's: read the contents with the honesty line
above in mind. Reference time in every record is the cycle time C.

### What "tm06" means

`tm06` is the product configuration: the model starts 6 h before the cycle time (hence "minus 6"), from
that earlier GFS cycle's analysis, and its first 6 h are spin-up. The soil (moisture, temperature, snow
water) is carried from the previous FrankenNAM cycle rather than taken from the GFS, because the GFS is
about 0.05 m3/m3 wetter than the NAM over CONUS. (The `tm00` in the file name is NOAA's own and is kept for
compatibility; it has nothing to do with `tm06`.) The design is in `docs/tm06-design.md` of the nam-recast
repository.

## Where

Free, no key: maps and the viewer at `nam.theconvergencezone.com/maps/`, and these files, for the re-run cases, at

```
https://nam.theconvergencezone.com/grids/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2
```

`status.json` and the per-date index (names, sizes, SHA-256) sit beside the files. Until DNS for the domain exists,
the same paths are served from the preview host `dzat3kduvlnwx.cloudfront.net`.

## Swap-in

Only the base changes. The examples use cycle 00Z on 1 Nov 2026.

### curl: one file, or one field by byte range

```sh
BASE=https://nam.theconvergencezone.com/grids/nam.20261101
F=nam.t00z.awphys24.tm00.grib2

# the whole file and its inventory
curl -s -O "$BASE/$F" -O "$BASE/$F.idx"

# only the 2 m temperature message: offsets come from the .idx
R=$(curl -s "$BASE/$F.idx" | awk -F: -v pat=':TMP:2 m above ground:' \
      '$0 ~ pat {s=$2; if ((getline) > 0) print s "-" ($2-1); else print s "-"; exit}')
curl -s -r "$R" "$BASE/$F" -o t2m.grib2
```

The `.idx` lines are `n:offset:d=YYYYMMDDHH:VAR:level:step:`; a message runs from its offset to the byte before
the next line's offset. (The awk and curl steps were tested against a local copy of the files; the HTTPS host
does not exist yet.)

### wgrib2

```sh
wgrib2 "$F" -match ':(TMP|DPT):2 m above ground:' -csv t2m_td2m.csv     # from the downloaded file
wgrib2 "$F" -s | head                                                    # inventory
```

wgrib2 reads these files as it reads the NAM's. [UNTESTED here: wgrib2 was not installed on the machine this
README was written on; the commands are the usual ones.]

### Python, Herbie

Any code that reads GRIB2 by byte range from an `.idx` needs only the new base URL. With ecCodes:

```python
import urllib.request, eccodes as ec
base = "https://nam.theconvergencezone.com/grids/nam.20261101/nam.t00z.awphys24.tm00.grib2"
rows = [l.split(":") for l in urllib.request.urlopen(base + ".idx").read().decode().splitlines()]
i = next(k for k, r in enumerate(rows) if r[3] == "TMP" and r[4] == "2 m above ground")
end = int(rows[i + 1][1]) - 1
req = urllib.request.Request(base, headers={"Range": f"bytes={rows[i][1]}-{end}"})
g = ec.codes_new_from_message(urllib.request.urlopen(req).read())
```

(The same byte-range read, from local files, is what the maps renderer uses.) For Herbie, point the NAM
`awphys` source at the same base; the `.idx` layout is the NOMADS one. [PLACEHOLDER: a tested Herbie snippet,
posted before launch.]

### BUFKIT

[PLACEHOLDER: the sounding product, its path and station list, once the sounding product
exists and has been tested.]

## Retention

Design plan: the last 30 days of cycles are kept (about 60 cycles, 2-3 GB each); the status index lists the
last 7 days. [DECISION NEEDED: Joe: confirm the retention before launch.]

## Contact

Operator: Joe Boomgard-Zagrodnik (sole proprietorship); contact via theconvergencezone.com/contact/. Terms: `terms.html` on the site.
