"""Colour scales. The first block (T2M, QPF, SNOW, PRECIP6, PWAT, GUST) is a verbatim
copy of ensplots/colormaps.py (WeatherBell-style discrete scales) so maps.theconvergencezone.com
and this site share their look; the scales below it are new to this site.
A scale is a list of (lower_edge, hex) rows plus a TOP, the last upper edge."""
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

T2M = [
    (-100, "#1b1f5c"), (-95, "#1d2a74"), (-90, "#1f3f86"), (-85, "#1f5b8c"), (-80, "#1f7a86"),
    (-75, "#2a8f78"), (-70, "#3c7d63"), (-65, "#4f5f5f"), (-60, "#5c5c5c"), (-55, "#6e6e6e"),
    (-50, "#858585"), (-45, "#a3a3a3"), (-40, "#c7c7c7"), (-35, "#e6d6ec"), (-30, "#f3c2dd"),
    (-25, "#f29ccb"), (-20, "#ea70b6"), (-15, "#dc41a0"), (-10, "#c0228a"), (-5, "#9b208c"),
    (0, "#6f2b9a"), (5, "#4a30a3"), (10, "#2f3cb3"), (15, "#2d5dcb"), (20, "#2f80dc"),
    (25, "#4aa8e6"), (30, "#3db9b9"), (35, "#2e9f6c"), (40, "#39b34b"), (45, "#8dd06c"),
    (50, "#cae6b8"), (55, "#e4e0c6"), (60, "#f4eea3"), (65, "#f6d566"), (70, "#f4ac41"),
    (75, "#e9602c"), (80, "#b8301f"), (85, "#991d18"), (90, "#7d1512"), (95, "#6a2a24"),
    (100, "#8c5a3c"), (105, "#b09070"), (110, "#7d7d7d"), (115, "#50608f"), (120, "#2f7f9c"),
    (125, "#2aa26b"), (130, "#1fbf42"),
]
T2M_TOP = 135

QPF = [
    (0, "#ffffff"), (0.01, "#d6d2d2"), (0.02, "#bfbaba"), (0.05, "#a29c9c"), (0.08, "#7f7979"),
    (0.1, "#caf0b1"), (0.15, "#a4e38d"), (0.2, "#79d46b"), (0.25, "#50bf4b"), (0.3, "#2fa833"),
    (0.4, "#1f8c2b"), (0.5, "#1a5fd0"), (0.6, "#3b82e0"), (0.7, "#5aa0ea"), (0.8, "#7dbcf2"),
    (0.9, "#a9d7f8"), (1, "#f6f6a1"), (1.2, "#f2dc5b"), (1.4, "#f2b43d"), (1.6, "#ee8c2b"),
    (1.8, "#e8622b"), (2, "#d83a2b"), (2.5, "#c02425"), (3, "#a01a1a"), (3.5, "#861414"),
    (4, "#6e1010"), (5, "#7a3a2a"), (6, "#5b4a3b"), (7, "#8a6a4a"), (8, "#b48a62"),
    (9, "#d9b48a"), (10, "#d1c9e8"), (11, "#b5a9dc"), (12, "#9989d0"), (13, "#7b69c4"),
    (14, "#5b4db4"), (15, "#3b2d9a"), (16, "#5b1b8a"), (17, "#7b1b9a"), (18, "#9b1ba8"),
    (19, "#c121b8"), (20, "#e131c8"),
]
QPF_TOP = 100

SNOW = [
    (0, "#ffffff"), (0.1, "#d9d9d9"), (0.5, "#bdbdbd"), (1, "#9e9e9e"), (1.5, "#737373"),
    (2, "#bfe0f7"), (2.5, "#9dcdf2"), (3, "#79b8ec"), (3.5, "#5aa3e4"), (4, "#3f8edb"),
    (4.5, "#2b78cf"), (5, "#1f62bf"), (5.5, "#184ea8"), (6, "#143b8f"), (6.5, "#3a2f8f"),
    (7, "#4f2d99"), (7.5, "#652ba3"), (8, "#7c2aad"), (8.5, "#952ab4"), (9, "#ae2bb8"),
    (9.5, "#c62db7"), (10, "#dc2fb0"), (11, "#ea3ea3"), (12, "#f1529a"), (13, "#f56694"),
    (14, "#f77a95"), (15, "#f88f9c"), (16, "#f9a3a8"), (17, "#fab6b6"), (18, "#fbc8c8"),
    (19, "#f3d2e4"), (20, "#e5d6f0"), (21, "#c8ecf6"), (22, "#a8e6f6"), (23, "#86dff5"),
    (24, "#63d6f2"), (25, "#45c9ea"), (26, "#34b6d8"), (27, "#2aa0c2"), (28, "#2c8db0"),
    (29, "#397fa6"), (30, "#4a789e"), (31, "#5a7598"), (32, "#687393"), (33, "#75728f"),
    (34, "#80718b"), (35, "#8a7190"), (36, "#937299"), (37, "#9c73a3"), (38, "#a474ad"),
    (39, "#ab76b7"), (40, "#b178c1"), (41, "#b67acb"), (42, "#ba7dd5"), (43, "#bd80de"),
    (44, "#c083e7"), (45, "#c287ef"), (46, "#c48bf5"), (47, "#c590fa"), (48, "#c695ff"),
]
SNOW_TOP = 200
# Map snow totals and depth (inches): the meteogram scale from 0.1 in up.
SNOW_MAP = SNOW[1:]

# 6-hour precipitation (inches) for the map loops: WeatherBell's 6-h precip bar.
# The first edge is the transparent threshold; values below 0.01 in draw nothing.
PRECIP6 = [
    (0.01, "#d9d9d9"), (0.05, "#b5b5b5"), (0.1, "#8f8f8f"), (0.2, "#b8ecb0"), (0.3, "#5fc95f"),
    (0.5, "#1f8f2f"), (0.7, "#1f55c8"), (0.9, "#4a8ee0"), (1.2, "#8ec6f2"), (1.6, "#f5e95a"),
    (2, "#f4b43c"), (3, "#ee7a2a"), (4, "#d93b24"), (5, "#a3141a"), (6, "#6e2a1e"),
    (8, "#b48a62"), (10, "#d6c6ea"), (12, "#ad92d9"), (14, "#8761c6"), (16, "#6e2aa5"),
    (18, "#b020a8"), (20, "#e34fd0"),
]
PRECIP6_TOP = 100

TCC = [(0, "#0a1830"), (10, "#102a52"), (20, "#163d74"), (30, "#1f5494"), (40, "#2d6eae"),
       (50, "#4a8bc2"), (60, "#6ea7d2"), (70, "#93c0df"), (80, "#b6d6ea"), (90, "#d9eaf4")]
TCC_TOP = 100.5

PWAT = [
    (0, "#ffffff"), (0.02, "#e6e6e6"), (0.04, "#d4d4d4"), (0.1, "#c2c2c2"), (0.15, "#afafaf"),
    (0.2, "#9c9c9c"), (0.25, "#8a8a8a"), (0.3, "#777777"), (0.35, "#8a7a3a"), (0.4, "#9a8a3c"),
    (0.45, "#aa9a40"), (0.5, "#b9a84a"), (0.55, "#c4a65c"), (0.6, "#cfa86c"), (0.65, "#d8ac7c"),
    (0.7, "#dfb48e"), (0.75, "#b4a8d8"), (0.8, "#a498d0"), (0.85, "#9487c8"), (0.9, "#8476c0"),
    (0.95, "#7466b8"), (1, "#6457b0"), (1.1, "#5a6cc0"), (1.2, "#4f80c8"), (1.3, "#3fa0a0"),
    (1.4, "#2fb080"), (1.5, "#38b860"), (1.6, "#8ac840"), (1.7, "#c0d030"), (1.8, "#e6d820"),
    (1.9, "#f0c020"), (2, "#f0a020"), (2.1, "#f08020"), (2.2, "#f06020"), (2.3, "#e84020"),
    (2.4, "#d82820"), (2.5, "#c01818"), (2.6, "#a01010"), (2.7, "#800808"), (2.8, "#a0208a"),
    (2.9, "#b030a0"), (3, "#9020a0"), (3.1, "#7010a0"), (3.2, "#5010b0"), (3.3, "#3020c0"),
    (3.4, "#2040d0"), (3.5, "#2060e0"), (3.6, "#2088e8"), (3.7, "#20a8f0"), (3.8, "#20c8f8"),
    (3.9, "#30e0f8"), (4, "#40f0ff"),
]
PWAT_TOP = 10

GUST = [
    (0, "#ffffff"), (10, "#ececec"), (12, "#dadada"), (14, "#c8c8c8"), (16, "#b4b4b4"),
    (18, "#c8ddf5"), (20, "#afcdf0"), (22, "#95bdeb"), (24, "#7badE5"), (26, "#619ddf"),
    (28, "#478dd8"), (30, "#2f7dd0"), (32, "#1e6cc4"), (34, "#2aa84a"), (36, "#3cb850"),
    (38, "#58c858"), (40, "#7ad860"), (42, "#e8e050"), (44, "#f0c840"), (46, "#f0a830"),
    (48, "#f08828"), (50, "#f06820"), (52, "#e84818"), (54, "#d83010"), (56, "#c02010"),
    (58, "#a81810"), (60, "#901010"), (62, "#780808"), (64, "#700c18"), (66, "#681028"),
    (68, "#601838"), (70, "#5a2a2a"), (74, "#6e3e2e"), (78, "#825234"), (82, "#96663c"),
    (86, "#aa7a48"), (90, "#be8e58"), (94, "#d0a26c"), (98, "#e0b684"), (102, "#e8e8e8"),
    (106, "#d8d8d8"), (110, "#c8c8c8"), (116, "#b4b4b4"), (120, "#a0a0a0"), (124, "#8c8c8c"),
    (128, "#787878"), (132, "#646464"), (136, "#505050"), (140, "#3c3c3c"), (150, "#282828"),
]
GUST_TOP = 300

def build(scale, top):
    bounds = [lo for lo, _ in scale] + [top]
    cmap = ListedColormap([c for _, c in scale]).with_extremes(bad="#d9d9d9", under=(0, 0, 0, 0))
    norm = BoundaryNorm(bounds, cmap.N, clip=False)
    return cmap, norm, bounds


# --- new to this site --------------------------------------------------------------
# Simulated composite reflectivity, dBZ: the familiar radar palette.
REFL = [
    (5, "#9ee0f0"), (10, "#5fc0e8"), (15, "#2f93d8"), (20, "#4fbf4f"), (25, "#2fa02f"),
    (30, "#1f7f1f"), (35, "#f2e84a"), (40, "#f0c030"), (45, "#ee8a28"), (50, "#e03a22"),
    (55, "#b01818"), (60, "#8a1260"), (65, "#c02ec0"), (70, "#f0f0f0"),
]
REFL_TOP = 80

# 700 hPa relative humidity, percent: dry brown to saturated green.
RH = [
    (0, "#a8743a"), (10, "#c29858"), (20, "#d9bc82"), (30, "#ece0b8"), (40, "#f6f2e0"),
    (50, "#e2f0d4"), (60, "#c4e4b4"), (70, "#9ad49a"), (80, "#66bf80"), (90, "#2f9c68"),
    (95, "#17775a"), (100, "#0e5a48"),
]
RH_TOP = 100.5

# Absolute vorticity at 500 hPa, 1e-5 s-1.
VORT = [
    (-10, "#ffffff"), (0, "#fff6d0"), (4, "#ffeaa0"), (8, "#ffd070"), (12, "#ffb040"), (16, "#fa8a28"),
    (20, "#ee6420"), (24, "#d83a24"), (28, "#b8202c"), (32, "#901a40"), (36, "#701a5c"), (40, "#501a72"),
]
VORT_TOP = 80

# Wind speed, knots.
WIND = [
    (0, "#ffffff"), (5, "#e4eef8"), (10, "#c6dcf0"), (15, "#9cc4e8"), (20, "#6aa6dc"), (25, "#4a8ad0"),
    (30, "#3a9a6a"), (35, "#58b848"), (40, "#a4cc3a"), (45, "#e8dc3a"), (50, "#f0b030"),
    (55, "#ee8028"), (60, "#e04a24"), (70, "#c01c28"), (80, "#901a40"), (90, "#6a1a60"),
]
WIND_TOP = 140

# CAPE, J kg-1.
CAPE = [
    (100, "#d6eef8"), (250, "#a4d8ee"), (500, "#6cc0e4"), (750, "#4fb890"), (1000, "#5cc04a"),
    (1500, "#c4d830"), (2000, "#f0d02c"), (2500, "#f0a428"), (3000, "#ee7226"), (4000, "#d83a24"),
    (5000, "#a8202c"), (6000, "#781a50"), (8000, "#d8a0e0"),
]
CAPE_TOP = 12000

# Precipitation type: index into this list (see fields.ptype).
PTYPE = [("Rain", "#3ca03c"), ("Snow", "#2a6ad8"), ("Freezing rain", "#e0307c"), ("Ice pellets", "#f09020")]

# Temperature, degrees F (T2M scale, 5 F bins); 850 hPa, degrees C, 2 C bins.
def _sample(scale, top, values):
    cmap, norm, _ = build(scale, top)
    from matplotlib.colors import to_hex
    return [to_hex(cmap(norm(v))) for v in values]


def resampled(scale, top, new_edges, src_lo, src_hi):
    """A new scale over new_edges whose colours walk the source scale from
    src_lo to src_hi (ensplots.colormaps.resampled): the T2m look reused for degrees C."""
    pos = np.linspace(src_lo, src_hi, len(new_edges))
    return list(zip(new_edges, _sample(scale, top, pos)))


T850 = resampled(T2M, T2M_TOP, list(range(-40, 41, 2)), -40, 120)
T850_TOP = 60
