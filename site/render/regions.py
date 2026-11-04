"""Regions: a lon/lat box each, turned into an extent on the native grid-218 Lambert plane.
maps.theconvergencezone.com has a single North America domain, so these cutouts are this
site's own proposal (see site/README.md, open questions)."""
from __future__ import annotations

import numpy as np
from pyproj import Proj, Transformer

from . import source

# name -> (label, west, east, south, north)
REGIONS = {
    "conus": ("CONUS", -126.0, -65.0, 22.5, 50.5),
    "northwest": ("Northwest", -126.0, -108.0, 40.0, 51.5),
    "southwest": ("Southwest", -125.0, -102.0, 29.5, 43.5),
    "rockies": ("Rockies and Plains", -117.5, -97.0, 34.5, 49.5),
    "central": ("Central US", -107.0, -84.0, 27.5, 49.0),
    "southeast": ("Southeast", -95.0, -74.0, 24.0, 38.5),
    "northeast": ("Northeast", -85.0, -66.0, 36.0, 48.0),
}


class Grid:
    """Grid-218 plane: x, y in metres on the Lambert conformal projection of the file."""

    def __init__(self, keys: dict):
        k = keys
        self.crs = (f"+proj=lcc +lat_1={k['Latin1InDegrees']} +lat_2={k['Latin2InDegrees']} "
                    f"+lat_0={k['LaDInDegrees']} +lon_0={k['LoVInDegrees'] - 360 if k['LoVInDegrees'] > 180 else k['LoVInDegrees']} "
                    f"+R={k['radius']} +units=m +no_defs")
        self.fwd = Transformer.from_crs("EPSG:4326", self.crs, always_xy=True)
        self.inv = Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)
        lon1 = k["longitudeOfFirstGridPointInDegrees"]
        lon1 = lon1 - 360 if lon1 > 180 else lon1
        self.x0, self.y0 = self.fwd.transform(lon1, k["latitudeOfFirstGridPointInDegrees"])
        self.dx, self.dy = k["DxInMetres"], k["DyInMetres"]
        self.x = self.x0 + self.dx * np.arange(source.NX)
        self.y = self.y0 + self.dy * np.arange(source.NY)
        self.extent = (self.x0 - self.dx / 2, self.x[-1] + self.dx / 2, self.y0 - self.dy / 2, self.y[-1] + self.dy / 2)

    def region_extent(self, name: str):
        _, w, e, s, n = REGIONS[name]
        t = np.linspace(0, 1, 60)
        lon = np.concatenate([w + (e - w) * t, np.full(60, e), e - (e - w) * t, np.full(60, w)])
        lat = np.concatenate([np.full(60, s), s + (n - s) * t, np.full(60, n), n - (n - s) * t])
        x, y = self.fwd.transform(lon, lat)
        gx0, gx1, gy0, gy1 = self.extent
        return (max(x.min(), gx0), min(x.max(), gx1), max(y.min(), gy0), min(y.max(), gy1))
