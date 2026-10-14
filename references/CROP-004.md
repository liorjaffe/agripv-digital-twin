# CROP-004 — Crop-cycle curve shape: missing development slowdown

## Citation

- Authors / organization: AgriPV project team
- Year: 2026
- Full title: Crop-cycle curve shape: missing development slowdown
- Journal / publisher / report: Internal model diagnosis and decision record
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not available
- Local source file (if retained): Not applicable
- Access date: Not applicable

## Source and scope

- Source type: Model diagnosis and software-display decision
- Site, cultivar, equipment, and study scale: Report crop-cycle simulations and the single preliminary SITE-003 weighing cycle
- What was measured or derived: Modeled field-cycle curve shape and preliminary site fresh-mass relative growth rates
- Relevant page, table, figure, equation, or dataset fields: `project/scenarios/crop_cycles.py`; generated model explorer and timeline series; SITE-003 weighings

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Highest absolute growth occurs near the end of modeled field cycles | Final-week differences in modeled fresh mass | g/plant/day | 7–13 g/plant/day | Prior report-cycle output; model has no development or maturity slowdown |
| Early measured fresh relative growth rate | SITE-003, 2026-09-02 to 2026-09-18 and 2026-09-18 to 2026-09-25 | d⁻¹ | 0.076/d and 0.188/d | Preliminary, single unfinished cycle; bed light channel unmapped |
| Early modeled fresh relative growth rate | Model comparison against SITE-003 | d⁻¹ | 0.17–0.24/d | Uncalibrated model; the comparison is not independent validation |
| Logistic mass curve versus accumulated thermal time | Carini et al. (2019), LETTUCE-013 | Not reported here | Abstract reports logistic models as best fit for lettuce fresh and dry mass | Abstract-level evidence only; no coefficients imported |

## Consequence 2: seasonal bias

The simulated open-channel cycles show higher cool-season harvest mass even
though their fixed-duration growth is lower. These are model-derived
comparisons, not observed yields.

| Transplant date | Field days | Mean T (°C) | Mean light (W/m²) | g/plant at harvest | g/plant after 26 days |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 Jan | 25 | 25.2 | 247 | 110 | 110 |
| 22 Feb | 26 | 24.8 | 262 | 130 | 130 |
| 18 May | 42 | 17.4 | 117 | 224 | 62 |
| 29 Jun | 45 | 16.9 | 121 | 251 | 62 |
| 13 Aug | 42 | 17.6 | 156 | 264 | 70 |

- Per day, the model grows less in winter: after the same 26 days from
  transplant, winter cycles reach 62–70 g/plant versus 110–130 g/plant in
  summer, consistent with their lower light.
- Winter harvests are larger only because the TC GDD-001 threshold of
  472.79 GDD takes 42–45 days at about 17°C versus 25–27 days at about 25°C.
  Total light per cycle is similar or lower in winter.
- Two model effects compound over those longer cycles: the VAN-001 structure
  loses less to respiration in cool air (the known inverted cold response
  documented in CROP-003), and the model has no maturity slowdown (CROP-004),
  so the additional days continue adding mass at the fastest modeled rate.
- Brazilian winter/summer lettuce trials provide context for a smaller
  seasonal difference: about 25–40% higher fresh mass in winter. Summer heat
  stress and bolting are not represented by this model. See
  [LETTUCE-014](./LETTUCE-014.md), [LETTUCE-015](./LETTUCE-015.md), and
  [LETTUCE-016](./LETTUCE-016.md); evidence is abstract-level and is not used
  as model parameters.
- Enabling TEMP-001 does not resolve the seasonal bias: its exploratory
  sensitivity produces 128–171 g/plant in winter versus 46–92 g/plant in
  summer. TEMP-001 remains disabled; its endpoints are unsupported and are
  not measured zero-growth thresholds.

## Connection to this project

- Reference ID and evidence role: CROP-004; report-display and model-limitation decision, not a calibration source
- Code file and symbol: `project/scenarios/crop_cycles.py`; report exports in `project/scenarios/generate_model_explorer.py` and `project/scenarios/export_model_timeline.py`
- Configuration key(s): Not applicable
- Related test(s): `project/tests/test_model_explorer.py`, `project/tests/test_timeline_export.py`, and `project/tests/test_fit_thermal_logistic.py`
- Adaptation made for this project: Each modeled bed cycle begins at transplant with the measured seedling state and runs through the TC GDD harvest threshold; the bed is replanted immediately. The off-bed ST interval is estimated backwards from the same temperature series for nursery planning only. A report-only logistic thermal-time fit utility is provided for future observations.
- Known differences or limitations: No growth values or model parameters are changed. The biomass model remains uncalibrated and not validated; cycle-1 weighings are preliminary and insufficient for fitting. The ODE still has no development or maturity slowdown, so modeled growth remains steepest at harvest. Seasonal comparisons are unreliable: longer cool-season cycles and lower modeled respiration produce about twice the summer harvest mass in this scenario, unlike the approximately 25–40% winter advantage reported in Brazilian trials.

## Validation record (if applicable)

- Dataset identity and version: Report crop cycles; SITE-003 cycle 1, 2026-09
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: The off-bed nursery stage is excluded from bed occupancy and biomass simulation; preliminary SITE-003 measurements remain excluded from parameter changes
- Metrics and uncertainty method: Relative growth rates and modeled final-mass fractions are descriptive comparisons; no uncertainty analysis performed
- Results and unresolved discrepancies: The Van Henten ODE has no development/maturity term, so its field-mass curves continue steeply until the GDD harvest threshold. SITE-003 shows slower early establishment than the model. These discrepancies remain unresolved.
- Reproduction command and output: `PYTHONPATH=. python project/scenarios/generate_model_explorer.py` and `PYTHONPATH=. python project/scenarios/export_model_timeline.py`

## Decision log

- Decision: Start each bed cycle at transplant and replant immediately after GDD harvest; nursery stays off-bed and is represented only by an estimated sowing date. Add a report-only warning against cross-season comparison. Do not tune establishment, temperature, or slowdown parameters; resolve seasonal bias with harvest weighings in every season (SITE-003 workflow / `lettuce-seedling-weighing`) and a thermal-time growth decline fitted with `project/validation/fit_thermal_logistic.py` after adequate measurements.
- Rationale: Nursery is off-bed in the field operation, while the current ODE does not represent maturity slowdown. The longer cool-season cycle and inverse modeled respiration response inflate cool-season totals. Current field data are preliminary and do not cover harvest. LETTUCE-010, LETTUCE-011, and LETTUCE-013 provide literature context for a thermal-time growth decline, not transferable fit parameters.
- Date: Not recorded
- Follow-up needed: Record harvest weighings in every season using the SITE-003 workflow; run `project/validation/fit_thermal_logistic.py`; consider LETTUCE-010 (Pearson, 1997), LETTUCE-011 (Wheeler et al., 1993), and LETTUCE-013 only after multi-season fitting.
