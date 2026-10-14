# CROP-003 — Crop-cycle biomass correction (October 2026): problem, diagnosis, fix

## Citation

- Authors / organization: AgriPV Digital Twin Prototype project
- Year: 2026
- Full title: Correction of inflated crop-cycle fresh mass after introducing TMY air temperature
- Journal / publisher / report: Project decision record
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not applicable
- Local source file (if retained): [`project/scenarios/crop_cycles.py`](../project/scenarios/crop_cycles.py), [`project/models/lettuce.py`](../project/models/lettuce.py)
- Access date: 2026-10-13

## Source and scope

- Source type: Internal diagnostic and decision record
- Site, cultivar, equipment, and study scale: Report crop cycles (model explorer, timeline, summary report)
- What was measured or derived: Cause of the ~2× increase in modeled fresh mass after commit `ec4b248` added `tmy_air_temperature.csv`
- Relevant page, table, figure, equation, or dataset fields: See below

### Symptom

After TMY air temperature replaced the synthetic/constant temperature, the open-channel model explorer reported 410–594 g fresh/plant per cycle (winter cycle 76 days, 594 g/plant), versus a grower-reported 100–300 g/plant.

### What was checked and is NOT the cause

- TMY file values (monthly means 16.7–25.0 °C) and UTC-to-local mapping in `load_tmy_air_temperature`
- GDD daily-mean calculation in `lettuce_development.py`
- Night-time respiration (dry biomass decreases in darkness)
- Temperature is not applied twice

### Causes found

1. **Nursery counted as field growth (logic error).** GDD-001 defines ST as sowing to *final transplant* (through maternity and nursery benches) and TC as final transplant to harvest. The biomass ODE previously ran from sowing at field density (96 plants / 11.25 m²) with 11 g/m² initial dry mass, so 20–32 nursery days were simulated as field growth.
2. **Inverted temperature response (model structure).** In the VAN-001 structure, cool air lowers maintenance respiration and the CO2 compensation point, so daily dry-mass gain *increases* as temperature falls (≈7.2 g/m²/day at 16 °C vs ≈5.5 at 26 °C, same light). Combined with the longer GDD cycle in winter (+55% duration), this produced the ~2.2× increase (1.39 × 1.55). Literature shows the opposite response (TEMP-001).

| Same winter light series (start 29 May), g fresh/plant | 43 days | 76 days |
| --- | --- | --- |
| Constant 26 °C | 275 | 394 |
| TMY (≈16.5 °C) | 383 | 594 |

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| ST = sowing to final transplant via maternity and nursery | GDD-001 thesis, p. 17 and list of abbreviations | Not applicable | Not applicable | Verified in library PDF |
| Transplant seedling mass | `TRANSPLANT_FRESH_MASS_G_PER_PLANT` | g/plant | 0.90 g fresh measured (SITE-003); dry = 0.045 g at 5 % | Replaced the earlier 0.23 g DW placeholder (≈4.6 g fresh), which was chosen after exploratory runs |
| Sensitivity to seedling dry-matter fraction | SITE-003 | g FW/plant | 5 % → 62–169; 9.8 % → 91–208 (open channel, completed cycles, TEMP-001 ON) | Seedling dry matter unmeasured |

## Connection to this project

- Reference ID and evidence role: CROP-003; decision record linking CROP-002, GDD-001, TEMP-001, LETTUCE-006 to LETTUCE-012
- Code file and symbol: `crop_cycles.simulate_repeated_crops` (each bed cycle begins at transplant and continues to GDD harvest; all in-bed rows have `cycle_stage="field"`; off-bed nursery sowing date is estimated backwards for planning), `transplant_initial_state_g_m2`, `TRANSPLANT_FRESH_MASS_G_PER_PLANT`; `lettuce.get_f_temp` (exploratory, off by default); `generate_model_explorer.cycle_summary_html` (incomplete cycles not compared); `lettuce_development` ST requirement corrected 398.67 → 398.64 GDD
- Configuration key(s): `cultivation` (plant density)
- Related test(s): `project/tests/test_crop_cycles.py`, `project/tests/test_lettuce.py`, `project/tests/test_model_explorer.py`
- Adaptation made for this project: Fix 1 starts field biomass from the transplanted seedling state, and beds are replanted immediately after each harvest; the ST nursery stage is off-bed. Fresh-mass equivalent is total field dry mass at harvest (including the transplanted seedling) / 0.05, no longer gain above 11 g/m²
- Known differences or limitations: See TEMP-001; dry-matter fraction (CROP-002, LETTUCE-009, LETTUCE-012) and seedling mass remain unmeasured

## Validation record (if applicable)

- Dataset identity and version: Period_Components.csv (2026) + tmy_air_temperature.csv
- Calibration or independent validation: Not performed. An exploratory check against cycle-1 weighings (SITE-003) shows early field growth about 4–6× faster than measured (default model); this single unfinished cycle is not used to change parameters
- Inclusion/exclusion and quality-control rules: Completed GDD cycles only
- Metrics and uncertainty method: Before/after comparison
- Results and unresolved discrepancies: Open channel, g fresh/plant: before 436 / 410 / 474 / 594 / 533 / 529; after (measured 0.90 g seedling, SITE-003; TEMP-001 off = default) 122.0 / 109.3 / 171.8 / 241.9 / 159.3 / 184.6; with TEMP-001 enabled 72.4 / 60.9 / 131.0 / 141.0 / 129.3 / 169.6; with the earlier 0.23 g DW placeholder 155.9 / 135.2 / 220.1 / 226.0 / 217.6 / 260.9 (Jan, Feb, Apr, May, Aug, Oct starts). Cool-season cycles remain heavier than summer cycles; LETTUCE-011 shows this can be real, but it is not validated
- Reproduction command and output: `PYTHONPATH=. python project/scenarios/generate_model_explorer.py` → `standalone/lettuce-pv-model-report.html`, section "Modeled crop-cycle estimates"

## Decision log

- Decision (revised 2026-10-13): Adopt fix 1 (transplant start, measured seedling) as a correction. Cause 2 (inverted cold response) is recorded as a KNOWN LIMITATION; TEMP-001 is kept only as an exploratory option, disabled by default
- Rationale: Starting each bed cycle at transplant follows the GDD-001 field-stage definition and the SITE-003 seedling measurement; nursery production occurs off-bed. TEMP-001 endpoints are not evidence of zero assimilation (6.1 °C is a phenology base, 32 °C the highest tested temperature), and seedling RGR does not define a canopy curve
- Date: 2026-10-13
- Follow-up needed:
  1. DONE for fresh mass (SITE-003, 0.90 g). Still open: seedling dry matter with a pooled sample on a finer scale
  2. Record dated harvests (fresh mass per plant, dry-matter content) per season
  3. Resolve the inverted cold response with the LETTUCE-010 thermal-time structure fitted to site harvests; re-run this comparison
  4. Follow the curve-shape and maturity-slowdown diagnosis in [CROP-004](./CROP-004.md); do not add a slowdown until supported by fitted parameters from more than one season
