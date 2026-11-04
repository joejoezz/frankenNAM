"""The product-plan field list. Each field is a function of the decoded frame (and, for the
accumulation fields, the cycle totals) returning drawing layers; help text for the "?" box
lives next to it. Units are US customary on the plot, as on maps.theconvergencezone.com."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter

from . import colormaps as cm

KT = 1.94384
LV = "entire atmosphere (considered as a single layer)"
KUCH_LEVELS = (1000, 925, 850, 700, 600, 500)

# key -> (idx var, idx level, is_accumulation). Instantaneous messages are "N hour fcst" or "anl".
INSTANT = {
    "mslet": ("MSLET", "mean sea level", False),
    "z500": ("HGT", "500 mb", False), "absv500": ("ABSV", "500 mb", False),
    "rh700": ("RH", "700 mb", False), "w700": ("VVEL", "700 mb", False),
    "t850": ("TMP", "850 mb", False), "u850": ("UGRD", "850 mb", False), "v850": ("VGRD", "850 mb", False),
    "t2": ("TMP", "2 m above ground", False), "d2": ("DPT", "2 m above ground", False),
    "u10": ("UGRD", "10 m above ground", False), "v10": ("VGRD", "10 m above ground", False),
    "refc": ("REFC", LV, False), "pwat": ("PWAT", LV, False),
    "csnow": ("CSNOW", "surface", False), "cicep": ("CICEP", "surface", False),
    "cfrzr": ("CFRZR", "surface", False), "crain": ("CRAIN", "surface", False),
    "cape": ("CAPE", "surface", False), "cin": ("CIN", "surface", False),
    "ps": ("PRES", "surface", False),
}
for _p in (1000, 925, 700, 600, 500):
    INSTANT[f"t{_p}"] = ("TMP", f"{_p} mb", False)

F = lambda k: (k - 273.15) * 1.8 + 32.0  # noqa: E731


def _clean(a):
    a = np.array(a, dtype=np.float32)
    a[np.abs(a) > 1e19] = np.nan
    return a


def _under(a, ps, hpa):
    """Mask pressure-level values below ground (surface pressure under the level)."""
    return np.where(ps >= hpa * 100.0, a, np.nan)


def smooth(a, sigma):
    return gaussian_filter(a, sigma)


def hl_centres(p_hpa, radius=24, prominence=3.0):
    """[(kind, value, i, j)] extremes of a (2r+1)-node window standing out by `prominence` hPa."""
    ps = smooth(p_hpa, 2.5)
    mx, mn = maximum_filter(ps, size=2 * radius + 1), minimum_filter(ps, size=2 * radius + 1)
    out = []
    edge = 6
    for kind, mask in (("L", (ps == mn) & (mx - ps >= prominence)), ("H", (ps == mx) & (ps - mn >= prominence))):
        for i, j in zip(*np.nonzero(mask)):
            if edge <= i < ps.shape[0] - edge and edge <= j < ps.shape[1] - edge:
                out.append((kind, int(round(float(ps[i, j]))), int(i), int(j)))
    return out


def fill(data, scale, top, ticks, unit, label=None, clip=False):
    return {"kind": "fill", "data": data, "scale": scale, "top": top, "ticks": ticks, "unit": unit, "label": label, "clip": clip}


def contour(data, levels, color="#000", width=1.1, dashed=False, labels=True, bold=None, fmt="%d"):
    return {"kind": "contour", "data": data, "levels": levels, "color": color, "width": width,
            "dashed": dashed, "labels": labels, "bold": bold, "fmt": fmt}


# ---- fields ---------------------------------------------------------------------------

def f_mslp_precip6(d, t, fhr):
    layers = []
    if t.get("p6") is not None:
        layers.append(fill(t["p6"] / 25.4, cm.PRECIP6, cm.PRECIP6_TOP,
                           [0.01, 0.1, 0.3, 0.5, 0.9, 1.6, 3, 5, 8, 12, 16, 20], "in"))
    p = smooth(_clean(d["mslet"]) / 100.0, 1.5)
    layers.append(contour(p, list(range(900, 1081, 4)), bold=1000))
    layers.append({"kind": "hl", "data": _clean(d["mslet"]) / 100.0})
    return layers, t.get("p6_label", "")


def f_z500_vort(d, t, fhr):
    ps = _clean(d["ps"])
    v = _under(_clean(d["absv500"]) * 1e5, ps, 500)
    z = smooth(_under(_clean(d["z500"]), ps, 500), 1.2)
    return [fill(v, cm.VORT, cm.VORT_TOP, [0, 8, 16, 24, 32, 40], "10⁻⁵ s⁻¹"),
            contour(z, list(range(4800, 6001, 60)), bold=5400, fmt="%d")], ""


def f_rh700_omega(d, t, fhr):
    ps = _clean(d["ps"])
    rh = _under(_clean(d["rh700"]), ps, 700)
    w = smooth(_under(_clean(d["w700"]), ps, 700), 1.2)
    return [fill(rh, cm.RH, cm.RH_TOP, [0, 20, 40, 60, 80, 90, 100], "%"),
            contour(w, [-3, -2, -1, -0.5, -0.25], color="#7a1fa2", width=1.0, labels=False)], ""


def f_t850_wind(d, t, fhr):
    ps = _clean(d["ps"])
    t850 = _under(_clean(d["t850"]) - 273.15, ps, 850)
    u = _under(_clean(d["u850"]), ps, 850) * KT
    v = _under(_clean(d["v850"]), ps, 850) * KT
    return [fill(t850, cm.window(cm.T850, -30, 30), 32, [-30, -20, -10, 0, 10, 20, 30], "°C", clip=True),
            contour(smooth(np.nan_to_num(t850, nan=20), 1.0), [0], color="#000", width=1.6, labels=False),
            {"kind": "barbs", "u": u, "v": v}], ""


def f_t2m(d, t, fhr):
    t2 = F(_clean(d["t2"]))
    return [fill(t2, cm.window(cm.T2M, -30, 115), 120, list(range(-30, 116, 10)), "°F", clip=True),
            contour(smooth(t2, 1.0), [32], color="#1a4fd8", width=1.5, labels=False)], ""


def f_td2m(d, t, fhr):
    td = F(_clean(d["d2"]))
    return [fill(td, cm.window(cm.T2M, -30, 80), 85, list(range(-30, 81, 10)), "°F", clip=True),
            contour(smooth(td, 1.0), [32], color="#1a4fd8", width=1.5, labels=False)], ""


def f_wind10(d, t, fhr):
    u, v = _clean(d["u10"]) * KT, _clean(d["v10"]) * KT
    return [fill(np.hypot(u, v), cm.WIND, cm.WIND_TOP, [0, 10, 20, 30, 40, 50, 60, 80], "kt"),
            {"kind": "barbs", "u": u, "v": v}], ""


def f_refl(d, t, fhr):
    return [fill(_clean(d["refc"]), cm.REFL, cm.REFL_TOP, [5, 15, 25, 35, 45, 55, 65], "dBZ")], ""


def f_ptype(d, t, fhr):
    cls = np.zeros(d["crain"].shape, dtype=np.float32)
    for i, k in enumerate(("crain", "csnow", "cicep", "cfrzr")):      # later wins: wintry over rain
        cls[_clean(d[k]) > 0.5] = i + 1
    return [{"kind": "ptype", "data": cls}], ""


def f_precip6(d, t, fhr):
    if t.get("p6") is None:
        return None, ""
    return [fill(t["p6"] / 25.4, cm.PRECIP6, cm.PRECIP6_TOP, [0.01, 0.1, 0.3, 0.5, 0.9, 1.6, 3, 5, 8, 12, 16, 20], "in")], t.get("p6_label", "")


def f_precip_total(d, t, fhr):
    if t.get("apcp") is None:
        return None, ""
    return [fill(t["apcp"] / 25.4, cm.PRECIP6, cm.PRECIP6_TOP, [0.01, 0.1, 0.3, 0.5, 0.9, 1.6, 3, 5, 8, 12, 16, 20], "in")], f"f000–f{fhr:03d}"


def f_snow10(d, t, fhr):
    if t.get("weasd") is None:
        return None, ""
    return [fill(t["weasd"] * 10 / 25.4, cm.SNOW_MAP, cm.SNOW_TOP, [0.1, 1, 2, 4, 6, 8, 10, 14, 18, 24, 30, 36, 48], "in")], f"f000–f{fhr:03d}"


def f_snowku(d, t, fhr):
    if t.get("kuch") is None:
        return None, ""
    return [fill(t["kuch"] / 25.4, cm.SNOW_MAP, cm.SNOW_TOP, [0.1, 1, 2, 4, 6, 8, 10, 14, 18, 24, 30, 36, 48], "in")], f"f000–f{fhr:03d}"


def f_cape_cin(d, t, fhr):
    cin = smooth(_clean(d["cin"]), 1.0)
    return [fill(_clean(d["cape"]), cm.CAPE, cm.CAPE_TOP, [100, 500, 1000, 2000, 3000, 4000, 6000, 8000], "J kg⁻¹"),
            contour(cin, [-200, -100, -50], color="#222", width=1.0, dashed=True, labels=True)], ""


def f_pwat(d, t, fhr):
    return [fill(_clean(d["pwat"]) / 25.4, cm.PWAT, cm.PWAT_TOP, [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], "in")], ""


# id -> (title, tab label, fn, needs-accumulation, help text). Help is at most three plain sentences.
FIELDS = {
    "mslp_precip6": ("MSLP and 6 h precipitation", "MSLP + precip", f_mslp_precip6,
                     "Sea-level pressure (hPa, every 4) over the precipitation that fell in the 6 h ending at the valid time. "
                     "H and L mark pressure centers; the first frames show the 3 h since the start. "
                     "Pressure is the NAM's own reduction (MSLET), smoothed lightly."),
    "z500_vort": ("500 hPa height and absolute vorticity", "500 hPa", f_z500_vort,
                  "Height contours every 60 m with the 5400 m line bold, over absolute vorticity. "
                  "Vorticity maxima trace the shortwaves that drive weather in the lower troposphere. "
                  "Blank where the 500 hPa level is below ground."),
    "rh700_omega": ("700 hPa relative humidity and omega", "700 RH + omega", f_rh700_omega,
                    "Relative humidity with contours of upward motion (omega, Pa s⁻¹: -0.25, -0.5, -1, -2, -3) in purple. "
                    "Moist air with strong ascent is where steady precipitation and heavy snow bands form. "
                    "Blank where 700 hPa is below ground."),
    "t850_wind": ("850 hPa temperature and wind", "850 T + wind", f_t850_wind,
                  "Temperature in °C with the 0 °C line in black and wind barbs in knots (full barb 10, flag 50). "
                  "The 850 hPa freezing line is a first guide to rain versus snow away from the mountains. "
                  "Blank where 850 hPa is below ground."),
    "t2m": ("2 m temperature", "2 m T", f_t2m,
            "Air temperature two meters above ground, in °F, with the freezing line in blue. "
            "Straight from the model's post-processed surface fields."),
    "td2m": ("2 m dew point", "2 m Td", f_td2m,
             "Dew point two meters above ground, in °F, with the 32 °F line in blue. "
             "Dew point is the moisture measure that matters for fog, frost, snow-versus-rain and storm fuel."),
    "wind10": ("10 m wind", "10 m wind", f_wind10,
               "Wind speed in knots with barbs (full barb 10, flag 50) ten meters above ground. "
               "Instantaneous model wind at the valid time, not a gust."),
    "refl": ("Simulated composite reflectivity", "Reflectivity", f_refl,
             "The radar echo the model's hydrometeors would produce, strongest return in the column, in dBZ. "
             "It is a model product: use it for storm mode and timing, not to compare cell by cell with observed radar."),
    "ptype": ("Precipitation type", "P-type", f_ptype,
              "The model's dominant surface precipitation type where it is precipitating: rain, snow, freezing rain or ice pellets. "
              "These are the four yes/no categorical fields the post-processor writes (CRAIN, CSNOW, CFRZR, CICEP); where more than one is set, the wintry type is drawn."),
    "precip6": ("6 h precipitation", "6 h precip", f_precip6,
                "Liquid-equivalent precipitation in the 6 h ending at the valid time, in inches. "
                "The first frame after the start covers 3 h."),
    "precip_total": ("Run-total precipitation", "Total precip", f_precip_total,
                     "Liquid-equivalent precipitation accumulated from the start of the forecast, in inches. "
                     "Built by summing the model's accumulation buckets."),
    "snow10": ("Run-total snowfall, 10:1", "Snow 10:1", f_snow10,
               "The model's liquid-equivalent snowfall since the start, times ten, in inches. "
               "A fixed ratio: it overstates snow depth in wet snow and understates it in cold, dry snow."),
    "snowku": ("Run-total snowfall, Kuchera", "Snow Kuchera", f_snowku,
               "Liquid-equivalent snowfall since the start, times the Kuchera ratio from the warmest temperature between the surface and 500 hPa, in inches. "
               "The ratio is 12 + (271.16 K minus that temperature), doubled where warmer, never below 0, using 3-hourly steps. "
               "It is a diagnostic, not a settled-depth forecast: no compaction, melting or wind."),
    "cape_cin": ("CAPE and CIN", "CAPE + CIN", f_cape_cin,
                 "Surface-based CAPE (J kg⁻¹) in color, with CIN (convective inhibition) contoured dashed at -50, -100 and -200. "
                 "Large CAPE with little CIN is the setup for deep convection once something triggers it."),
    "pwat": ("Precipitable water", "PWAT", f_pwat,
             "Water vapor in the whole column, expressed as inches of liquid water. "
             "High values mean more moisture available to rain out."),
}
# Order shown in the viewer; "needs accumulation" fields have no f00 frame.
NEEDS_ACC = {"precip6", "precip_total", "snow10", "snowku"}
