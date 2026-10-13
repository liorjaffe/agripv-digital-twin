# CROP-002 — Biomass initialization, dry-matter conversion, and synthetic temperature

## Citation

- Authors / organization: AgriPV Digital Twin Prototype project
- Year: 2026
- Full title: Crop-cycle biomass and temperature scenario assumptions
- Journal / publisher / report: Project assumption register
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not applicable
- Local source file (if retained): [`project/scenarios/crop_cycles.py`](../project/scenarios/crop_cycles.py)
- Access date: 2026-10-13

## Source and scope

- Source type: Model assumptions; no retained measurement source
- Site, cultivar, equipment, and study scale: Report-only crop cycles for a
  curly-lettuce scenario; not site-validated
- What was measured or derived: Dry-matter fraction, initial state, and a
  synthetic seasonal temperature curve used to derive report biomass and
  harvest timing.
- Relevant page, table, figure, equation, or dataset fields: Constants and
  `seasonal_mean_temp_c` / `seasonal_canopy_temperature` in
  `project/scenarios/crop_cycles.py`; initial state constants in
  `project/models/lettuce.py`.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Dry-matter fraction of fresh mass | `DRY_MATTER_FRACTION_OF_FRESH_MASS` | Fraction | 0.05 (5%) | Similar-crop primary data in LETTUCE-005 derive 5.3–6.6% for hydroponic red-leaf ‘Red Wave’; this does not establish a curly-lettuce range or site value |
| Initial structural/non-structural dry biomass | `DEFAULT_INITIAL_STRUCTURAL_DRY_BIOMASS_G_M2`, `DEFAULT_INITIAL_NONSTRUCTURAL_DRY_BIOMASS_G_M2` | g/m² | 8 / 3; total 11; structural share 72.7% | No transplant measurement or primary literature source verified; this is not the cited 30/70 structural/non-structural split |
| Transplant seedling mass (crop cycles) | `TRANSPLANT_FRESH_MASS_G_PER_PLANT` × `SEEDLING_DRY_MATTER_FRACTION` in `crop_cycles.py` | g/plant | 0.90 g fresh (measured, SITE-003) × 0.05 = 0.045 g DW; 8:3 structural split | Fresh mass measured; seedling dry-matter fraction assumed |
| Published hydroponic dry-matter range | LETTUCE-009, LETTUCE-012 | % | 2.6–4.9 % | 0.05 sits at/above this range; lower DMF raises fresh-mass estimates |
| Site dry-matter content, cycle 1 (preliminary) | SITE-003, weighings 18.09 and 25.09 | % | ≈ 9.8–9.9 % | Single unfinished cycle; 5 h at 90 °C drying may not reach constant mass; NOT used yet |
| Synthetic seasonal temperature | `seasonal_mean_temp_c` and `seasonal_canopy_temperature` | °C; day of year | `20.5 + 5 cos(2π(day−34)/365.25)`, then shifted to 24 °C on planting day | Entirely synthetic. No site temperature channel is used by this report method. |

## Connection to this project

- Reference ID and evidence role: CROP-002; explicit model assumptions
- Code file and symbol: [`project/scenarios/crop_cycles.py`](../project/scenarios/crop_cycles.py),
  `DRY_MATTER_FRACTION_OF_FRESH_MASS`, `seasonal_mean_temp_c`,
  `seasonal_canopy_temperature`; [`project/models/lettuce.py`](../project/models/lettuce.py),
  initial-state constants
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_model_explorer.py`](../project/tests/test_model_explorer.py),
  [`project/tests/test_timeline_export.py`](../project/tests/test_timeline_export.py)
- Adaptation made for this project: Since CROP-003 (2026-10) the fixed
  dry-matter fraction converts total modeled field dry mass at harvest
  (including the transplanted seedling) to a fresh-mass equivalent; the
  8 + 3 g/m² default initial state is no longer used by crop cycles (it remains
  the default for `simulate_growth_timeseries` and the continuous pipeline); supplied TMY air
  temperature is used for report-only thermal development and temperature
  response, with a synthetic curve retained only as a fallback for callers
  that do not provide temperature.
- Known differences or limitations: The curve is not observed weather; the
  dry-matter fraction and initial state are not cultivar/site measurements.
  LETTUCE-005 provides adjacent hydroponic evidence for a different lettuce
  type, not a general dry-matter range.

## Validation record

- Dataset identity and version: No site temperature series or transplant
  biomass record retained
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Not applicable
- Metrics and uncertainty method: Not applicable
- Results and unresolved discrepancies: LETTUCE-005 reports data from which
  a 5.3–6.6% whole-plant dry-matter fraction can be derived for ‘Red Wave’;
  a curly/hydroponic Crespa range remains unverified. Existing biomass
  initialization differs from the review-cited 30/70 split, for which no
  primary source was identified. The report's GDD clock sets cycle duration
  while the biomass model accumulates throughout that duration and has no
  site-calibrated marketable-yield ceiling. In a same-light diagnostic, the
  TMY-driven cool-season cycle lasted 76 days and reached 5,072.5 g/m² modeled
  fresh-mass equivalent; a constant-26°C sensitivity lasted 43 days and reached
  2,407.8 g/m². This roughly 2.1× difference is driven by the modeled cycle
  lasting longer, not by applying temperature twice or changing irradiance.
  At the configured 96 plants / 11.25 m², those equivalents are about 594 and
  282 g/plant, respectively. The user reports a usual 100–300 g/plant range,
  but dated per-cycle records are not currently retained, so this is a
  plausibility comparison rather than calibration. These are outputs of
  uncalibrated assumptions, not evidence that winter site yield is higher.
- Reproduction command and output: Report-generation scripts; outputs remain
  scenario illustrations, not measured crop predictions.

## Decision log

- Update 2026-10-13: See [CROP-003](./CROP-003.md) for the crop-cycle
  correction, the new transplant placeholder, and before/after results.

- Decision: Retain 0.05 as a disclosed scenario assumption; use LETTUCE-005
  only as adjacent evidence that this order of magnitude is plausible for
  one hydroponic red-leaf cultivar. Show biomass and fresh-mass outputs in
  reports as clearly labeled uncalibrated model scenarios, never as measured
  or validated production. Keep the initial biomass explicitly synthetic/
  unmeasured.
- Rationale: The adjacent study does not establish the site's curly cultivar
  composition, transplant state, or temperature course.
- Date: 2026-10-13
- Follow-up needed:
  - Obtain primary curly/hydroponic Crespa harvest-composition studies and
    document the dry-matter range and measurement protocol.
  - Measure transplant structural and non-structural dry mass or locate the
    primary model initialization source; reconcile the present 8/3 g/m² state
    with the attributed 30/70 split before claiming it as a literature default.
  - Obtain site canopy-temperature records and measured harvest/dry-mass
    observations paired with verified channel units and locations; calibrate
    and validate the growth, GDD, and fresh-mass conversion before treating
    report scenarios as production predictions.
