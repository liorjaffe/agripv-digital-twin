# TEMP-001 — Exploratory air-temperature factor on assimilation (OFF by default)

## Citation

- Authors / organization: AgriPV Digital Twin Prototype project (method synthesis)
- Year: 2026
- Full title: Trapezoidal air-temperature factor on canopy assimilation for the VAN-001 lettuce model
- Journal / publisher / report: Project method/assumption register
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not applicable
- Local source file (if retained): [`project/models/lettuce.py`](../project/models/lettuce.py), `get_f_temp`
- Access date: 2026-10-13

## Source and scope

- Source type: Exploratory sensitivity setting; NOT an established correction. Endpoints are borrowed values, not measured assimilation limits
- Site, cultivar, equipment, and study scale: Disabled by default; when enabled it affects all biomass simulations (crop-cycle reports and the continuous `run_timeseries` state)
- What was measured or derived: A dimensionless factor f(T) in [0, 1] multiplying canopy assimilation `f_phot` in `lettuce_rhs`
- Relevant page, table, figure, equation, or dataset fields: See evidence table

Equation (T = hourly air temperature, °C):

```
f(T) = 0                                   T <= T_min  or  T >= T_max
f(T) = (T - T_min) / (T_opt_low - T_min)   T_min < T < T_opt_low
f(T) = 1                                   T_opt_low <= T <= T_opt_high
f(T) = (T_max - T) / (T_max - T_opt_high)  T_opt_high < T < T_max
```

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Problem: VAN-001 structure gains more dry mass in cool air | Project diagnostic (CROP-003) | g/m²/day | ≈7.2 at 16 °C vs ≈5.5 at 26 °C, equal light | Respiration Q10 = 2 (ref 25 °C) and CO2 compensation point fall with T; only `r_gr` slows (Q10 = 1.6) |
| Temperature is "relatively less important" in the Van Henten lettuce model | Van Henten (1994) PhD thesis, abstract, ch. 3 sensitivity analysis, https://doi.org/10.18174/205106 | Not applicable | Not derived | Explains why the model needs an explicit limitation |
| Cool air strongly reduces lettuce RGR | [LETTUCE-006](./LETTUCE-006.md) | g/g/day | 0.11 at 10 °C vs 0.35 at 22 °C | Seedling stage |
| `T_min` = 6.1 °C | [GDD-001](./GDD-001.md), TC base temperature | °C | 6.1 | A phenology (development) base temperature, NOT evidence that assimilation is zero at 6.1 °C |
| `T_opt_low` = 22 °C | [LETTUCE-006](./LETTUCE-006.md), [LETTUCE-007](./LETTUCE-007.md) | °C | 22 | Development-rate maximum (Brunini); high RGR at 22 °C (Scaife) |
| `T_opt_high` = 24 °C | [LETTUCE-008](./LETTUCE-008.md), [LETTUCE-009](./LETTUCE-009.md) | °C | 24 | Max dry mass at 24 °C air (hydroponic); leaf-expansion traits peak near 24 °C |
| `T_max` = 32 °C | [LETTUCE-009](./LETTUCE-009.md) highest tested air temperature | °C | 32 | Only the highest TESTED temperature; NOT evidence of zero assimilation |
| Scope of LETTUCE-006 RGR values | [LETTUCE-006](./LETTUCE-006.md) | g/g/day | Not derived | Seedlings ≤ 0.2 g DW; supports the direction of the response, NOT a whole-canopy assimilation curve |

## Connection to this project

- Reference ID and evidence role: TEMP-001; exploratory sensitivity option, disabled by default
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py) — `LettuceParams.apply_temperature_factor`, `t_min_growth_c`, `t_opt_low_c`, `t_opt_high_c`, `t_max_growth_c`; `get_f_temp`; `lettuce_rhs`
- Configuration key(s): Not applicable; enable with `LettuceParams(apply_temperature_factor=True)` for sensitivity runs. Default `False` keeps all outputs on the unmodified VAN-001 structure
- Related test(s): `project/tests/test_lettuce.py::test_temperature_factor_is_off_by_default_and_trapezoidal_when_enabled`, `::test_default_model_keeps_known_inverted_cold_response`, `::test_enabled_temperature_factor_reverses_cold_response`
- Adaptation made for this project: Applied hourly to assimilation as a lumped growth-rate limitation (Scaife reports NAR and LAR affected about equally; Carotti notes photosynthesis itself is weakly temperature-dependent, so this is NOT a photosynthesis mechanism)
- Known differences or limitations: Not fitted; hourly application penalises hot afternoons more than a daily-mean factor; no thermal-time decline of RGR (LETTUCE-010/011); root-zone temperature not represented

## Validation record (if applicable)

- Dataset identity and version: TMY air temperature + Period_Components open channel (0A–0E), 2026
- Calibration or independent validation: Not performed (sensitivity only)
- Inclusion/exclusion and quality-control rules: Completed GDD cycles only
- Metrics and uncertainty method: One-at-a-time sensitivity, g fresh/plant per completed cycle
- Results and unresolved discrepancies: see table below
- Reproduction command and output: `simulate_repeated_crops(hourly, "light_open_w_m2", temperature_c=...)` with parameter overrides

Sensitivity computed with the earlier 0.23 g DW seedling placeholder (before SITE-003); relative differences between cases still apply.

| Case (open channel, g fresh/plant) | Jan | Feb | Apr | May | Aug | Oct |
| --- | --- | --- | --- | --- | --- | --- |
| Factor ON (6.1 / 22 / 24 / 32 °C) | 156 | 137 | 219 | 224 | 217 | 260 |
| Factor OFF (current default) | 214 | 196 | 267 | 333 | 250 | 277 |
| ON, `T_min` = 10 °C (Brunini) | 156 | 137 | 204 | 187 | 206 | 258 |
| ON, `T_opt_low` = 20 °C | 156 | 137 | 245 | 262 | 238 | 267 |
| ON, `T_max` = 30 °C | 135 | 117 | 218 | 224 | 217 | 257 |

## Decision log

- Decision (revised 2026-10-13 after code review): Keep the factor in code but DISABLED by default; do not present it as a correction
- Rationale: Review pointed out that 6.1 °C is a phenology base temperature, 32 °C is only the highest tested temperature, and seedling RGR values do not establish a canopy assimilation curve; enabling it by default would change every biomass simulation, including the continuous pipeline, on unsupported endpoints
- Date: 2026-10-13
- Follow-up needed: Address the inverted cold response properly (thermal-time coupled structure, [LETTUCE-010](./LETTUCE-010.md) / [LETTUCE-011](./LETTUCE-011.md)), fitted to site harvest records ([SITE-003](./SITE-003.md) and later cycles); only then reconsider a default temperature response. Port nothing to the dashboard
