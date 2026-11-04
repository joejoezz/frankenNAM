"""Shared constants for the verification package."""
import os, datetime as dt
from pathlib import Path

DATA = Path(os.environ.get("NR_VERIFY_DATA", Path.home() / "data" / "nam-recast-verify"))
CACHE, OBS, WORK = DATA / "cache", DATA / "obs", DATA / "work"
for _p in (CACHE, OBS, WORK): _p.mkdir(parents=True, exist_ok=True)
OURS = "nam-recast-617711905691"
USER_AGENT = "nam-recast-verify/0.1 (research; low request rate)"

# case id (product cycle C, YYYYMMDDHH) -> short description. P = C - 6 h is the GFS cycle used by tm06.
CASES = {
    "2026110100": "Phase 0 case (quiet-ish autumn, CONUS-wide)",
    "2026012312": "CAD ice storm, GA/Carolinas",
    "2025010512": "Snowcrete, DC (snow to sleet)",
    "2025012100": "Gulf Coast snow",
    "2024111912": "PNW bomb cyclone + atmospheric river",
    "2025031412": "Plains severe + blizzard",
    "2025122912": "Lake-effect / Great Lakes snow, late Dec 2025",
}
PTYPE_CASES = ("2026012312", "2025010512", "2025012100")     # p-type verification
SNOTEL_CASES = ("2024111912", "2025031412")
LEADS = list(range(0, 85, 3))

def cycle(c): return dt.datetime.strptime(c, "%Y%m%d%H")

REGIONS = {
    "NE": "ME NH VT MA RI CT NY NJ PA DE MD DC",
    "SE": "VA WV NC SC GA FL AL MS TN KY LA AR",
    "Midwest": "OH IN IL MI WI MN IA MO",
    "Plains": "ND SD NE KS OK TX",
    "West": "MT WY CO NM AZ UT NV ID WA OR CA",
}
STATE_REGION = {s: r for r, ss in REGIONS.items() for s in ss.split()}
STATES = sorted(STATE_REGION)
