# Scorecard: NAM (archived), FrankenNAM, fnew against observations

Cases (1): `2026012312` CAD ice storm, GA/Carolinas.

## 1. Surface stations, all cases pooled (CONUS ASOS/AWOS)

Model minus observation; bias, MAE, RMSE. Bold = lowest MAE or RMSE in the row. Bilinear interpolation; T and Td corrected to station elevation (6.5 and 2 K/km); common sample across models.

**2 m temperature (K)**

| lead | n | bias NAM (archived) | bias FrankenNAM | bias fnew | MAE NAM (archived) | MAE FrankenNAM | MAE fnew | RMSE NAM (archived) | RMSE FrankenNAM | RMSE fnew |
|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 18068 | +0.61 | +0.65 | +0.47 | **1.85** | 2.21 | 2.01 | **2.44** | 2.83 | 2.62 |
| 27-48 h | 18020 | +1.02 | +1.46 | +0.97 | 2.32 | 2.62 | **2.26** | 3.05 | 3.39 | **2.98** |
| 51-84 h | 26908 | +1.30 | +1.93 | +1.35 | **2.36** | 2.82 | 2.45 | **3.12** | 3.61 | 3.22 |
| 12-84 h | 56183 | +1.14 | +1.60 | +1.12 | **2.27** | 2.65 | 2.31 | **3.01** | 3.42 | 3.04 |

**2 m dew point (K)**

| lead | n | bias NAM (archived) | bias FrankenNAM | bias fnew | MAE NAM (archived) | MAE FrankenNAM | MAE fnew | RMSE NAM (archived) | RMSE FrankenNAM | RMSE fnew |
|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 17998 | +0.63 | +0.26 | -0.26 | **2.04** | 2.34 | 2.41 | **2.71** | 3.01 | 3.13 |
| 27-48 h | 17971 | +0.92 | +0.99 | +0.48 | **2.37** | 2.70 | 2.48 | **3.24** | 3.63 | 3.39 |
| 51-84 h | 26777 | +0.87 | +1.52 | +0.93 | **2.55** | 3.10 | 2.80 | **3.31** | 3.93 | 3.61 |
| 12-84 h | 55950 | +0.85 | +1.13 | +0.59 | **2.43** | 2.84 | 2.64 | **3.21** | 3.69 | 3.47 |

**10 m wind speed (m/s)**

| lead | n | bias NAM (archived) | bias FrankenNAM | bias fnew | MAE NAM (archived) | MAE FrankenNAM | MAE fnew | RMSE NAM (archived) | RMSE FrankenNAM | RMSE fnew |
|---|---|---|---|---|---|---|---|---|---|---|
| 3-24 h | 17925 | +0.44 | +0.49 | +0.47 | **1.39** | 1.43 | 1.41 | **1.79** | 1.83 | 1.81 |
| 27-48 h | 17724 | +0.24 | +0.29 | +0.27 | **1.32** | 1.36 | 1.35 | **1.73** | 1.78 | 1.77 |
| 51-84 h | 26485 | +0.58 | +0.61 | +0.60 | **1.73** | 1.77 | 1.77 | **2.29** | 2.33 | 2.32 |
| 12-84 h | 55355 | +0.47 | +0.51 | +0.49 | **1.54** | 1.58 | 1.57 | **2.05** | 2.08 | 2.07 |

## 2. By region, 12-84 h, all cases pooled (RMSE / bias)

**2 m temperature (K)**

| region | n | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|---|
| CONUS | 56183 | 3.01 / +1.14 | 3.42 / +1.60 | 3.04 / +1.12 |
| NE | 5474 | 2.10 / +0.82 | 2.42 / +1.04 | 2.20 / +0.72 |
| SE | 15620 | 2.72 / -0.00 | 2.80 / +0.23 | 2.69 / -0.00 |
| Midwest | 12360 | 3.04 / +2.14 | 3.93 / +3.00 | 3.10 / +1.99 |
| Plains | 10644 | 3.24 / +1.84 | 3.79 / +2.55 | 3.35 / +1.99 |
| West | 12085 | 3.43 / +1.13 | 3.63 / +1.38 | 3.44 / +1.08 |

**2 m dew point (K)**

| region | n | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|---|
| CONUS | 55950 | 3.21 / +0.85 | 3.69 / +1.13 | 3.47 / +0.59 |
| NE | 5454 | 2.88 / +1.48 | 2.95 / +1.44 | 2.79 / +1.07 |
| SE | 15506 | 2.93 / +0.17 | 3.16 / +0.27 | 3.15 / -0.12 |
| Midwest | 12317 | 3.36 / +1.90 | 4.32 / +2.78 | 3.71 / +1.82 |
| Plains | 10636 | 3.16 / +1.50 | 3.70 / +2.14 | 3.39 / +1.55 |
| West | 12037 | 3.58 / -0.21 | 3.93 / -0.45 | 3.95 / -0.82 |

**10 m wind speed (m/s)**

| region | n | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|---|
| CONUS | 55355 | 2.05 / +0.47 | 2.08 / +0.51 | 2.07 / +0.49 |
| NE | 5334 | 2.25 / +0.85 | 2.33 / +0.91 | 2.33 / +0.88 |
| SE | 15390 | 2.25 / +0.78 | 2.27 / +0.82 | 2.28 / +0.84 |
| Midwest | 12369 | 1.68 / +0.61 | 1.74 / +0.71 | 1.72 / +0.64 |
| Plains | 10245 | 2.04 / -0.01 | 2.06 / -0.05 | 2.04 / -0.03 |
| West | 12017 | 2.03 / +0.18 | 2.07 / +0.20 | 2.05 / +0.17 |

## 3. By case, 12-84 h, CONUS RMSE (lowest in bold)

**2 m temperature (K)**

| case | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|
| `2026012312` CAD ice storm, GA/Carolinas | **3.01** | 3.42 | 3.04 |

**2 m dew point (K)**

| case | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|
| `2026012312` CAD ice storm, GA/Carolinas | **3.21** | 3.69 | 3.47 |

**10 m wind speed (m/s)**

| case | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|
| `2026012312` CAD ice storm, GA/Carolinas | **2.05** | 2.08 | 2.07 |

**Interpolation sensitivity, RMSE 12-84 h, CONUS, all cases**

| interp | variable | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|---|
| bilinear | 2 m temperature | 3.006 | 3.422 | 3.044 |
| bilinear | 2 m dew point | 3.212 | 3.694 | 3.474 |
| bilinear | 10 m wind speed | 2.046 | 2.084 | 2.075 |
| nearest | 2 m temperature | 3.018 | 3.435 | 3.057 |
| nearest | 2 m dew point | 3.238 | 3.719 | 3.501 |
| nearest | 10 m wind speed | 2.055 | 2.093 | 2.084 |

## 4. 24 h precipitation against MRMS (0.25 degree boxes over the lower 48)

MRMS product per case: `2026012312` MultiSensor_QPE_24H_Pass2_00.00. Windows ending C+24/48/72/84 h (the last is 60-84 h). ETS and frequency bias (FBI) from contingency counts summed over cases and windows; MAE in mm over all valid boxes.

| threshold | ETS NAM (archived) | ETS FrankenNAM | ETS fnew | FBI NAM (archived) | FBI FrankenNAM | FBI fnew |
|---|---|---|---|---|---|---|
| >= 2.5 mm | **0.649** | 0.607 | 0.610 | 1.19 | 1.23 | 1.22 |
| >= 10.0 mm | 0.559 | **0.580** | 0.570 | 1.03 | 1.04 | 1.03 |
| >= 25.0 mm | **0.405** | 0.335 | 0.341 | 0.95 | 0.84 | 0.85 |

|  | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|
| MAE (mm / 24 h) | **1.92** | 2.09 | 2.08 |
| mean bias (mm / 24 h) | +0.32 | +0.36 | +0.34 |
| mean observed (mm / 24 h) | 3.33 |  |  |

**ETS by case** (NAM (archived) / FrankenNAM / fnew)

| case | >= 2.5 mm | >= 10.0 mm | >= 25.0 mm |
|---|---|---|---|
| `2026012312` | 0.65 / 0.61 / 0.61 | 0.56 / 0.58 / 0.57 | 0.41 / 0.33 / 0.34 |

**ETS by window** (NAM (archived) / FrankenNAM / fnew)

| window | >= 2.5 mm | >= 10 mm |
|---|---|---|
| C+24 h | 0.56 / 0.55 / 0.56 | 0.31 / 0.51 / 0.51 |
| C+48 h | 0.66 / 0.60 / 0.61 | 0.56 / 0.53 / 0.54 |
| C+72 h | 0.77 / 0.69 / 0.70 | 0.72 / 0.73 / 0.72 |
| C+84 h | 0.50 / 0.48 / 0.46 | 0.35 / 0.32 / 0.27 |

## 5. Precipitation type against ASOS present weather

Station-hours (3-hourly) where the station reports precipitation of a known type. The model type is the categorical flag (CRAIN/CSNOW/CFRZR/CICEP) at the nearest grid point; priority FZRA > ICEP > SNOW > RAIN; NONE = no flag set. Agreement = the model type is among the observed types (a mixed report such as RASN accepts either). Recall by observed type is the share of those hours the model got right.

| case | area | lead | n obs-hours | NAM (archived) | FrankenNAM | fnew |
|---|---|---|---|---|---|---|
| `2026012312` | event region | 3-36 h | 123 | 25.2% | **32.5%** | 28.5% |
| `2026012312` | event region | 39-84 h | 1133 | 38.6% | **39.3%** | **39.3%** |
| `2026012312` | CONUS | 3-36 h | 3818 | **60.1%** | 56.1% | 55.9% |
| `2026012312` | CONUS | 39-84 h | 7265 | **66.6%** | 63.4% | 63.3% |

Event regions (lat, lon boxes): `2026012312` 31.0-37.5 N, 87.0-77.0 W; `2025010512` 36.0-41.0 N, 80.0-74.0 W; `2025012100` 27.0-33.0 N, 98.0-82.0 W.

`2026012312` event region, NAM (archived): rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 302 | 0 | 47 | 6 | 235 |
| SNOW | 529 | 29 | 97 | 100 | 192 | 111 |
| FZRA | 117 | 16 | 1 | 53 | 25 | 22 |
| ICEP | 8 | 0 | 0 | 0 | 6 | 2 |
| MIX | 12 | 0 | 0 | 4 | 7 | 1 |

`2026012312` event region, FrankenNAM: rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 305 | 0 | 53 | 6 | 226 |
| SNOW | 529 | 27 | 119 | 87 | 198 | 98 |
| FZRA | 117 | 17 | 1 | 46 | 36 | 17 |
| ICEP | 8 | 0 | 0 | 0 | 7 | 1 |
| MIX | 12 | 0 | 0 | 2 | 7 | 3 |

`2026012312` event region, fnew: rows = observed, columns = model

| obs | n | RAIN | SNOW | FZRA | ICEP | NONE |
|---|---|---|---|---|---|---|
| RAIN | 590 | 296 | 0 | 68 | 7 | 219 |
| SNOW | 529 | 25 | 122 | 82 | 206 | 94 |
| FZRA | 117 | 16 | 1 | 45 | 37 | 18 |
| ICEP | 8 | 0 | 0 | 0 | 8 | 0 |
| MIX | 12 | 0 | 0 | 3 | 7 | 2 |
