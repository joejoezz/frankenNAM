"""FrankenNAM map renderer: one cycle of grid-218 awphys GRIB2 -> PNG frames.
Public entry point for the Lambda pattern: render.render_frame(cycle, field, region, fhr, src, out)."""
from .api import render_frame, render_cycle, FIELDS, REGIONS  # noqa: F401
