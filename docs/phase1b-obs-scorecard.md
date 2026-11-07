# Scorecard: NAM (archived), GFS (same cycle), GFS (6 h older cycle), FrankenNAM against observations

Cases (5): `2026110100` Phase 0 case (autumn, CONUS-wide); `2026012312` CAD ice storm, GA/Carolinas; `2025010512` Snowcrete, DC (snow to sleet); `2025012100` Gulf Coast snow; `2024111912` PNW bomb cyclone + atmospheric river.

## 1. Surface stations, all cases pooled (CONUS ASOS/AWOS)

Model minus observation; bias, MAE, RMSE. Bold = lowest MAE or RMSE in the row. Bilinear interpolation; T and Td corrected to station elevation (6.5 and 2 K/km); common sample across models.

**2 m temperature (K)**

| lead | n | bias NAM (archived) | bias GFS (same cycle) | bias GFS (6 h older cycle) | bias FrankenNAM | MAE NAM (archived) | MAE GFS (same cycle) | MAE GFS (6 h older cycle) | MAE FrankenNAM | RMSE NAM (archived) | RMSE GFS (same cycle) | RMSE GFS (6 h older cycle) | RMSE FrankenNAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 89257 | +0.36 | +0.51 | +0.52 | +0.38 | 1.65 | **1.63** | 1.70 | 1.81 | 2.28 | **2.25** | 2.34 | 2.45 |
| 27-48 h | 88400 | +0.23 | +0.45 | +0.50 | +0.20 | 1.94 | **1.88** | 1.91 | 2.00 | 2.63 | **2.58** | 2.63 | 2.68 |
| 51-84 h | 133979 | +0.22 | +0.45 | +0.46 | +0.17 | 2.17 | **2.17** | 2.21 | 2.27 | **2.88** | 2.93 | 2.98 | 2.99 |
| 12-84 h | 278098 | +0.26 | +0.47 | +0.49 | +0.23 | 2.00 | **1.98** | 2.03 | 2.09 | **2.70** | 2.72 | 2.77 | 2.79 |

**2 m dew point (K)**

| lead | n | bias NAM (archived) | bias GFS (same cycle) | bias GFS (6 h older cycle) | bias FrankenNAM | MAE NAM (archived) | MAE GFS (same cycle) | MAE GFS (6 h older cycle) | MAE FrankenNAM | RMSE NAM (archived) | RMSE GFS (same cycle) | RMSE GFS (6 h older cycle) | RMSE FrankenNAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 88884 | +0.33 | -0.70 | -0.72 | -0.60 | **1.87** | 2.10 | 2.14 | 2.16 | **2.58** | 2.79 | 2.84 | 2.99 |
| 27-48 h | 88176 | +0.00 | -0.41 | -0.36 | -0.54 | **2.15** | 2.19 | 2.18 | 2.33 | **2.93** | 2.93 | 2.93 | 3.18 |
| 51-84 h | 133569 | -0.07 | -0.05 | -0.03 | -0.42 | 2.41 | **2.39** | 2.43 | 2.66 | 3.23 | **3.19** | 3.24 | 3.55 |
| 12-84 h | 277203 | +0.01 | -0.28 | -0.26 | -0.48 | **2.24** | 2.27 | 2.30 | 2.46 | 3.04 | **3.03** | 3.07 | 3.34 |

**10 m wind speed (m/s)**

| lead | n | bias NAM (archived) | bias GFS (same cycle) | bias GFS (6 h older cycle) | bias FrankenNAM | MAE NAM (archived) | MAE GFS (same cycle) | MAE GFS (6 h older cycle) | MAE FrankenNAM | RMSE NAM (archived) | RMSE GFS (same cycle) | RMSE GFS (6 h older cycle) | RMSE FrankenNAM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 88459 | +0.52 | +0.53 | +0.52 | +0.50 | 1.45 | **1.45** | 1.47 | 1.46 | **1.91** | 1.91 | 1.93 | 1.92 |
| 27-48 h | 87520 | +0.39 | +0.43 | +0.40 | +0.36 | **1.51** | 1.53 | 1.53 | 1.51 | 2.00 | 2.02 | 2.02 | **1.99** |
| 51-84 h | 132709 | +0.56 | +0.37 | +0.32 | +0.54 | 1.65 | **1.63** | 1.63 | 1.64 | 2.17 | 2.15 | 2.15 | **2.14** |
| 12-84 h | 275432 | +0.50 | +0.43 | +0.39 | +0.47 | 1.57 | 1.57 | 1.57 | **1.57** | 2.07 | 2.08 | 2.08 | **2.06** |

## 2. By region, 12-84 h, all cases pooled (RMSE / bias)

**2 m temperature (K)**

| region | n | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|---|
| CONUS | 278098 | 2.70 / +0.26 | 2.72 / +0.47 | 2.77 / +0.49 | 2.79 / +0.23 |
| NE | 27074 | 2.84 / +0.55 | 2.45 / +0.25 | 2.51 / +0.20 | 2.81 / +0.46 |
| SE | 77428 | 2.32 / +0.08 | 2.35 / +0.08 | 2.32 / +0.04 | 2.42 / +0.05 |
| Midwest | 62720 | 2.49 / +0.18 | 2.43 / +0.41 | 2.52 / +0.41 | 2.69 / +0.13 |
| Plains | 52583 | 2.62 / +0.58 | 2.66 / +0.72 | 2.77 / +0.84 | 2.73 / +0.58 |
| West | 58293 | 3.32 / +0.17 | 3.51 / +0.91 | 3.56 / +1.00 | 3.36 / +0.13 |

**2 m dew point (K)**

| region | n | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|---|
| CONUS | 277203 | 3.04 / +0.01 | 3.03 / -0.28 | 3.07 / -0.26 | 3.34 / -0.48 |
| NE | 26985 | 2.71 / +0.94 | 2.78 / +1.03 | 2.79 / +0.82 | 2.57 / +0.33 |
| SE | 76952 | 2.80 / -0.49 | 2.78 / -0.22 | 2.81 / -0.25 | 3.26 / -1.01 |
| Midwest | 62585 | 2.86 / +0.05 | 2.91 / -0.28 | 3.05 / -0.30 | 3.15 / -0.21 |
| Plains | 52499 | 2.98 / +0.00 | 2.98 / -0.47 | 3.04 / -0.33 | 3.27 / -0.34 |
| West | 58182 | 3.66 / +0.22 | 3.59 / -0.82 | 3.55 / -0.67 | 3.97 / -0.57 |

**10 m wind speed (m/s)**

| region | n | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|---|
| CONUS | 275432 | 2.07 / +0.50 | 2.08 / +0.43 | 2.08 / +0.39 | 2.06 / +0.47 |
| NE | 26616 | 2.15 / +0.93 | 2.06 / +0.60 | 2.10 / +0.60 | 2.12 / +0.82 |
| SE | 76619 | 2.04 / +0.82 | 2.05 / +0.77 | 2.03 / +0.73 | 2.04 / +0.76 |
| Midwest | 62526 | 1.97 / +0.61 | 1.94 / +0.52 | 1.92 / +0.45 | 1.91 / +0.57 |
| Plains | 51829 | 2.00 / +0.04 | 2.09 / +0.43 | 2.11 / +0.42 | 1.99 / +0.10 |
| West | 57842 | 2.25 / +0.19 | 2.24 / -0.22 | 2.25 / -0.25 | 2.26 / +0.16 |

## 3. By case, 12-84 h, CONUS RMSE (lowest in bold)

**2 m temperature (K)**

| case | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|
| `2026110100` Phase 0 case (autumn, CONUS-wide) | 2.50 | **2.33** | 2.42 | 2.56 |
| `2026012312` CAD ice storm, GA/Carolinas | **3.00** | 3.03 | 3.10 | 3.04 |
| `2025010512` Snowcrete, DC (snow to sleet) | **2.39** | 2.63 | 2.61 | 2.42 |
| `2025012100` Gulf Coast snow | 3.12 | **3.09** | 3.18 | 3.32 |
| `2024111912` PNW bomb cyclone + atmospheric river | 2.43 | **2.42** | 2.43 | 2.54 |

**2 m dew point (K)**

| case | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|
| `2026110100` Phase 0 case (autumn, CONUS-wide) | **2.49** | 2.52 | 2.60 | 2.65 |
| `2026012312` CAD ice storm, GA/Carolinas | **3.21** | 3.40 | 3.48 | 3.47 |
| `2025010512` Snowcrete, DC (snow to sleet) | 2.77 | 2.87 | **2.77** | 2.78 |
| `2025012100` Gulf Coast snow | 3.77 | **3.52** | 3.60 | 4.37 |
| `2024111912` PNW bomb cyclone + atmospheric river | 2.80 | **2.75** | 2.79 | 3.18 |

**10 m wind speed (m/s)**

| case | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|
| `2026110100` Phase 0 case (autumn, CONUS-wide) | 2.00 | 2.07 | 2.11 | **1.96** |
| `2026012312` CAD ice storm, GA/Carolinas | **2.05** | 2.10 | 2.12 | 2.07 |
| `2025010512` Snowcrete, DC (snow to sleet) | 2.02 | 2.01 | **1.99** | 2.03 |
| `2025012100` Gulf Coast snow | 2.00 | **1.91** | 1.96 | 2.04 |
| `2024111912` PNW bomb cyclone + atmospheric river | 2.29 | 2.28 | 2.20 | **2.18** |

**Interpolation sensitivity, RMSE 12-84 h, CONUS, all cases**

| interp | variable | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|---|
| bilinear | 2 m temperature | 2.703 | 2.715 | 2.766 | 2.795 |
| bilinear | 2 m dew point | 3.037 | 3.033 | 3.071 | 3.342 |
| bilinear | 10 m wind speed | 2.075 | 2.076 | 2.077 | 2.057 |
| nearest | 2 m temperature | 2.716 | 2.766 | 2.815 | 2.807 |
| nearest | 2 m dew point | 3.066 | 3.114 | 3.151 | 3.372 |
| nearest | 10 m wind speed | 2.084 | 2.117 | 2.117 | 2.065 |

## 4. 24 h precipitation against MRMS (0.25 degree boxes over the lower 48)

MRMS product per case: `2026110100` MultiSensor_QPE_24H_Pass2_00.00; `2026012312` MultiSensor_QPE_24H_Pass2_00.00; `2025010512` MultiSensor_QPE_24H_Pass2_00.00; `2025012100` MultiSensor_QPE_24H_Pass2_00.00; `2024111912` MultiSensor_QPE_24H_Pass2_00.00. Windows ending C+24/48/72/84 h (the last is 60-84 h). ETS and frequency bias (FBI) from contingency counts summed over cases and windows; MAE in mm over all valid boxes.

| threshold | ETS NAM (archived) | ETS GFS (same cycle) | ETS GFS (6 h older cycle) | ETS FrankenNAM | FBI NAM (archived) | FBI GFS (same cycle) | FBI GFS (6 h older cycle) | FBI FrankenNAM |
|---|---|---|---|---|---|---|---|---|
| >= 2.5 mm | 0.566 | **0.604** | 0.585 | 0.552 | 1.11 | 1.11 | 1.09 | 1.07 |
| >= 10.0 mm | 0.510 | **0.573** | 0.549 | 0.510 | 1.03 | 1.01 | 0.98 | 0.95 |
| >= 25.0 mm | 0.347 | **0.390** | 0.371 | 0.325 | 0.98 | 0.95 | 0.90 | 0.91 |

|  | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|
| MAE (mm / 24 h) | 1.75 | **1.54** | 1.60 | 1.76 |
| mean bias (mm / 24 h) | +0.13 | +0.14 | +0.08 | +0.02 |
| mean observed (mm / 24 h) | 2.57 |  |  |  |

**ETS by case** (NAM (archived) / GFS (same cycle) / GFS (6 h older cycle) / FrankenNAM)

| case | >= 2.5 mm | >= 10.0 mm | >= 25.0 mm |
|---|---|---|---|
| `2026110100` | 0.48 / 0.55 / 0.51 / 0.48 | 0.37 / 0.45 / 0.44 / 0.39 | 0.23 / 0.28 / 0.28 / 0.23 |
| `2026012312` | 0.65 / 0.63 / 0.61 / 0.61 | 0.56 / 0.61 / 0.57 / 0.57 | 0.41 / 0.35 / 0.31 / 0.34 |
| `2025010512` | 0.51 / 0.52 / 0.54 / 0.51 | 0.77 / 0.73 / 0.76 / 0.72 | 0.49 / 0.58 / 0.48 / 0.42 |
| `2025012100` | 0.45 / 0.47 / 0.43 / 0.45 | 0.58 / 0.58 / 0.57 / 0.49 | 0.36 / 0.32 / 0.31 / 0.34 |
| `2024111912` | 0.56 / 0.65 / 0.63 / 0.54 | 0.50 / 0.59 / 0.55 / 0.48 | 0.39 / 0.54 / 0.55 / 0.40 |

**ETS by window** (NAM (archived) / GFS (same cycle) / GFS (6 h older cycle) / FrankenNAM)

| window | >= 2.5 mm | >= 10 mm |
|---|---|---|
| C+24 h | 0.60 / 0.62 / 0.62 / 0.61 | 0.59 / 0.64 / 0.63 / 0.59 |
| C+48 h | 0.57 / 0.60 / 0.59 / 0.55 | 0.53 / 0.58 / 0.56 / 0.51 |
| C+72 h | 0.58 / 0.61 / 0.60 / 0.58 | 0.49 / 0.60 / 0.57 / 0.52 |
| C+84 h | 0.48 / 0.54 / 0.50 / 0.44 | 0.37 / 0.42 / 0.37 / 0.36 |

## 5. Precipitation type against ASOS present weather

Station-hours (3-hourly) where the station reports precipitation of a known type. The model type is the categorical flag (CRAIN/CSNOW/CFRZR/CICEP) at the nearest grid point; priority FZRA > ICEP > SNOW > RAIN; NONE = no flag set. Agreement = the model type is among the observed types (a mixed report such as RASN accepts either). Recall by observed type is the share of those hours the model got right.

| case | area | lead | n obs-hours | NAM (archived) | GFS (same cycle) | GFS (6 h older cycle) | FrankenNAM |
|---|---|---|---|---|---|---|---|
| `2026012312` | event region | 3-36 h | 123 | 25.2% | 52.0% | **58.5%** | 28.5% |
| `2026012312` | event region | 39-84 h | 1133 | 38.6% | **42.9%** | 42.4% | 39.3% |
| `2026012312` | CONUS | 3-36 h | 3818 | 60.1% | **63.8%** | 62.5% | 55.9% |
| `2026012312` | CONUS | 39-84 h | 7265 | **66.6%** | 65.4% | 62.1% | 63.3% |
| `2025010512` | event region | 3-36 h | 528 | 76.1% | **80.1%** | 78.4% | 76.7% |
| `2025010512` | event region | 39-84 h | 233 | 51.9% | 49.8% | 45.5% | **52.8%** |
| `2025010512` | CONUS | 3-36 h | 3881 | **63.6%** | 61.8% | 61.3% | 60.6% |
| `2025010512` | CONUS | 39-84 h | 2706 | **46.0%** | 40.2% | 41.4% | 44.4% |
| `2025012100` | event region | 3-36 h | 488 | 44.9% | **78.1%** | 77.5% | 51.0% |
| `2025012100` | event region | 39-84 h | 28 | 21.4% | 21.4% | 32.1% | **35.7%** |
| `2025012100` | CONUS | 3-36 h | 1755 | 61.6% | **66.5%** | 63.0% | 53.7% |
| `2025012100` | CONUS | 39-84 h | 2138 | **45.6%** | 39.5% | 36.0% | 43.4% |

Event regions (lat, lon boxes): `2026012312` 31.0-37.5 N, 87.0-77.0 W; `2025010512` 36.0-41.0 N, 80.0-74.0 W; `2025012100` 27.0-33.0 N, 98.0-82.0 W.

`2026012312` event region, NAM (archived): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 302 | 0 | 47 | 6 | 235 |
| SNOW | 529 | 29 | 97 | 100 | 192 | 111 |
| FZRA | 117 | 16 | 1 | 53 | 25 | 22 |
| ICEP | 8 | 0 | 0 | 0 | 6 | 2 |
| MIX | 12 | 0 | 0 | 4 | 7 | 1 |

`2026012312` event region, GFS (same cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 301 | 6 | 48 | 6 | 229 |
| SNOW | 529 | 18 | 173 | 115 | 132 | 91 |
| FZRA | 117 | 8 | 11 | 62 | 23 | 13 |
| ICEP | 8 | 0 | 1 | 0 | 6 | 1 |
| MIX | 12 | 0 | 0 | 2 | 6 | 4 |

`2026012312` event region, GFS (6 h older cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 299 | 8 | 86 | 8 | 189 |
| SNOW | 529 | 11 | 179 | 94 | 152 | 93 |
| FZRA | 117 | 5 | 14 | 58 | 27 | 13 |
| ICEP | 8 | 0 | 1 | 0 | 7 | 0 |
| MIX | 12 | 1 | 1 | 2 | 6 | 2 |

`2026012312` event region, FrankenNAM: rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 296 | 0 | 68 | 7 | 219 |
| SNOW | 529 | 25 | 122 | 82 | 206 | 94 |
| FZRA | 117 | 16 | 1 | 45 | 37 | 18 |
| ICEP | 8 | 0 | 0 | 0 | 8 | 0 |
| MIX | 12 | 0 | 0 | 3 | 7 | 2 |

`2025010512` event region, NAM (archived): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 80 | 51 | 3 | 10 | 4 | 12 |
| SNOW | 649 | 3 | 457 | 3 | 19 | 167 |
| FZRA | 24 | 6 | 0 | 10 | 7 | 1 |
| ICEP | 4 | 0 | 0 | 0 | 2 | 2 |
| MIX | 4 | 0 | 2 | 0 | 2 | 0 |

`2025010512` event region, GFS (same cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 80 | 55 | 8 | 7 | 4 | 6 |
| SNOW | 649 | 9 | 475 | 2 | 13 | 150 |
| FZRA | 24 | 7 | 7 | 6 | 3 | 1 |
| ICEP | 4 | 0 | 0 | 1 | 1 | 2 |
| MIX | 4 | 0 | 3 | 0 | 0 | 1 |

`2025010512` event region, GFS (6 h older cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 80 | 44 | 6 | 6 | 3 | 21 |
| SNOW | 649 | 6 | 466 | 1 | 13 | 163 |
| FZRA | 24 | 6 | 6 | 8 | 2 | 2 |
| ICEP | 4 | 0 | 2 | 1 | 0 | 1 |
| MIX | 4 | 0 | 3 | 0 | 0 | 1 |

`2025010512` event region, FrankenNAM: rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 80 | 50 | 2 | 5 | 2 | 21 |
| SNOW | 649 | 6 | 465 | 3 | 34 | 141 |
| FZRA | 24 | 7 | 2 | 7 | 5 | 3 |
| ICEP | 4 | 0 | 0 | 1 | 3 | 0 |
| MIX | 4 | 0 | 2 | 0 | 1 | 1 |

`2025012100` event region, NAM (archived): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 115 | 57 | 0 | 7 | 5 | 46 |
| SNOW | 384 | 2 | 167 | 17 | 76 | 122 |
| FZRA | 3 | 0 | 0 | 1 | 2 | 0 |
| ICEP | 6 | 0 | 0 | 2 | 0 | 4 |
| MIX | 8 | 0 | 0 | 2 | 1 | 5 |

`2025012100` event region, GFS (same cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 115 | 70 | 5 | 1 | 8 | 31 |
| SNOW | 384 | 6 | 314 | 6 | 19 | 39 |
| FZRA | 3 | 0 | 0 | 1 | 1 | 1 |
| ICEP | 6 | 0 | 6 | 0 | 0 | 0 |
| MIX | 8 | 0 | 2 | 1 | 3 | 2 |

`2025012100` event region, GFS (6 h older cycle): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 115 | 75 | 2 | 2 | 10 | 26 |
| SNOW | 384 | 5 | 310 | 5 | 15 | 49 |
| FZRA | 3 | 0 | 2 | 0 | 1 | 0 |
| ICEP | 6 | 0 | 6 | 0 | 0 | 0 |
| MIX | 8 | 0 | 4 | 1 | 1 | 2 |

`2025012100` event region, FrankenNAM: rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 115 | 73 | 0 | 5 | 10 | 27 |
| SNOW | 384 | 4 | 183 | 5 | 58 | 134 |
| FZRA | 3 | 0 | 0 | 1 | 2 | 0 |
| ICEP | 6 | 0 | 1 | 2 | 0 | 3 |
| MIX | 8 | 0 | 0 | 1 | 3 | 4 |

## 6. SNOTEL 24 h precipitation (western mountain stations)

Gauge resolution 0.1 in; model sampled bilinearly at the station location without terrain adjustment, so ratios mix model skill with the 12 km / 0.25 degree terrain smoothing. Ratio = sum(model)/sum(obs) over station-windows.

| case | model | n | stations | obs mean mm | model mean mm | ratio | MAE mm | corr |
|---|---|---|---|---|---|---|---|---|
| `2024111912` | NAM (archived) | 2989 | 809 | 6.4 | 5.5 | 0.87 | 4.3 | 0.69 |
| `2024111912` | GFS (same cycle) | 2989 | 809 | 6.4 | 4.5 | 0.71 | 3.9 | 0.72 |
| `2024111912` | GFS (6 h older cycle) | 2989 | 809 | 6.4 | 4.2 | 0.66 | 3.8 | 0.75 |
| `2024111912` | FrankenNAM | 2989 | 809 | 6.4 | 4.7 | 0.73 | 4.3 | 0.69 |
