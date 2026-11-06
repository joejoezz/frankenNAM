# verify/: observation-based verification

Setup (clean checkout, Python 3.12; wgrib2 is not needed, eccodes comes from the pip wheel):

    python3 -m venv ~/data/nam-recast-verify/venv && ~/data/nam-recast-verify/venv/bin/pip install -r verify/requirements.txt
    cd ~/projects/nam-recast && ~/data/nam-recast-verify/venv/bin/python -m verify.run_baseline --case 2026110100 --models nam,gfs
    ... -m verify.run_baseline --all --models nam,gfs,gfs06          # all seven cases -> docs/baseline-scorecard.md
    ... -m verify.test_verify                                         # fast self-checks, no network

Everything downloaded or cached lives under `~/data/nam-recast-verify/` (`NR_VERIFY_DATA` overrides): `obs/` (ASOS, MRMS boxes, SNOTEL),
`cache/` (byte-range subsets of the model files: 2 m T/Td, 10 m wind, APCP, p-type flags, terrain, land), `work/` (per-case
station and box samples). First run of a case pulls observations (IEM ASOS is throttled to one request per ~4 s plus 429 backoff,
about 10-15 min per case) and ~1.5 MB of model data per forecast hour per model. Reruns are cached.

Modules: `obs_asos`, `obs_mrms`, `obs_snotel` (observations), `gribio` (idx byte-range reads, model specs, interpolation),
`score` (station, precipitation, p-type, SNOTEL metrics, kept as sums so cases pool exactly), `run_baseline` (orchestration,
tables, figures), `stage_case` (hindcast input staging into the nam-recast bucket).

FrankenNAM output drops in as a model: `--models nam,gfs,fnam` reads
`s3://nam-recast-617711905691/cases/<case>/products/nam.YYYYMMDD/nam.tCCz.awphysFF.tm00.grib2` (+ `.idx`), or any template:
`--models "nam,fr=/path/nam.{ymd}/nam.t{hh}z.awphys{fh:02d}.tm00.grib2@0"` (the `@N` is the init offset in hours from C, `gfs06` is `@-6`).
Use `--tag` to write a separate scorecard (`docs/<tag>-scorecard.md`, `docs/figs/<tag>/`, `verify/results/<tag>/`);
`verify/reading_<tag>.md`, if present, is inserted as the narrative reading at the top.

Phase 1 hindcast (`docs/phase1-scorecard.md`): `fnam-anl` is the analysis-start reference arm
(`cases/<case>/recast-anl/products/`). `fields` reads whole fields (MSLP, Z500, T850, 2 m T/Td, 10 m wind,
CAPE, REFC, p-type flags, 0-10 cm soil moisture, APCP) by byte range for any model; `hindcast` writes the gate
tables (`gate`), grid-to-grid statistics against the archived NAM (`g2g`), the tm06-vs-anl analysis (`ref`) and
the feature 9-panels with MRMS composite reflectivity (`features`; valid times picked from the archived NAM
only); `frozen_soil` measures the frozen share of soil water over cold land.

    ... -m verify.run_baseline --case 2026110100,2026012312,2025010512,2025012100,2024111912 --models nam,gfs,gfs06,fnam --tag phase1-obs
    ... -m verify.run_baseline --case 2025010512 --models nam,gfs,gfs06,fnam,fnam-anl --tag phase1-ref --no-fig
    ... -m verify.hindcast gate --obs-tag phase1-obs --ref-tag phase1-ref
    ... -m verify.hindcast g2g --case <cases> --models fnam,fnam-anl,gfs,gfs06
    ... -m verify.hindcast features --case <cases>;  ... -m verify.hindcast ref --case 2025010512
    ... -m verify.frozen_soil 2025010512 nam,fnam,fnam-anl 0,24,48
