# SITE-003 — Seedling weighing at final transplant (cycle 1, September 2026)

## Citation

- Authors / organization: AgriPV project field team (user-supplied "Lettuce Seedling Weighing Log")
- Year: 2026
- Full title: Lettuce Seedling Weighing Log, block "0_FRESH (WET) WEIGHT — LETTUCE SAMPLES" and "0_DRY WEIGHT — OVEN-DRYING METHOD"
- Journal / publisher / report: Internal field record
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not available
- Local source file (if retained): [`project/data/field/seedling_weighing_2026-09-02.csv`](../project/data/field/seedling_weighing_2026-09-02.csv) (transcribed from a screenshot of the log)
- Access date: 2026-10-13

## Source and scope

- Source type: Site measurement (destructive weighing)
- Site, cultivar, equipment, and study scale: AgriPV site, curly lettuce seedlings at planting into the beds ("a couple of weeks old"), 6 plants; oven drying 90 °C, window 12:00–17:00
- What was measured or derived: Fresh mass and leaf count per seedling at final transplant; attempted dry mass (bag method)
- Relevant page, table, figure, equation, or dataset fields: Log blocks 0_FRESH and 0_DRY, date 02.09.26

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Seedling fresh mass at final transplant | 0_FRESH, samples 1–6 | g/plant | mean 0.90 g, SD 0.09 g, n = 6 (range 0.77–1.04) | Single transplant date; representative stage per user |
| Leaf count at transplant | 0_FRESH | leaves | mean 8.3 (8–9) | Stage descriptor |
| Seedling dry mass | 0_DRY, bag replicates | g/plant | Not usable (NaN) | Values −0.10 to 0.07 g: below scale/bag resolution, as noted in the log |
| Later weighings 18.09 and 25.09 (10 bed positions each) | Blocks 1_ and 2_ | g/plant | 18.09: fresh 3.03 ± 1.32, dry 0.29 ± 0.11; 25.09: fresh 11.29 ± 5.98, dry 1.08 ± 0.51; dry matter ≈ 9.8–9.9 % | PRELIMINARY, single unfinished cycle; NOT used for parameters. Drying 5 h at 90 °C may not reach constant mass |

## Connection to this project

- Reference ID and evidence role: SITE-003; site measurement of the transplant state (model initial condition)
- Code file and symbol: [`project/scenarios/crop_cycles.py`](../project/scenarios/crop_cycles.py) `TRANSPLANT_FRESH_MASS_G_PER_PLANT = 0.90`, `SEEDLING_DRY_MATTER_FRACTION`, derived `TRANSPLANT_DRY_MASS_G_PER_PLANT`
- Configuration key(s): Not applicable
- Related test(s): `project/tests/test_crop_cycles.py` (uses the constant symbolically)
- Adaptation made for this project: Dry mass = 0.90 g × `SEEDLING_DRY_MATTER_FRACTION` (currently the 5 % output fraction) = 0.045 g/plant, so the seedling contributes exactly 0.90 g to reported harvest fresh mass. Replaces the 0.23 g DW placeholder (≈4.6 g fresh) introduced in CROP-003
- Known differences or limitations: One transplant date, n = 6; seedling dry-matter fraction unmeasured

## Validation record (if applicable)

- Dataset identity and version: Cycle 1, transplant 2026-09-02
- Calibration or independent validation: Not performed
- Inclusion/exclusion and quality-control rules: Dry weights excluded (negative / below resolution)
- Metrics and uncertainty method: Mean, SD
- Results and unresolved discrepancies: Sensitivity of completed-cycle fresh mass (open channel, g/plant, Jan/Feb/Apr/May/Aug/Oct), computed with the exploratory TEMP-001 factor ON: seedling DM 5 % (0.045 g DW) → 73 / 62 / 130 / 139 / 129 / 169; DM 9.8 % (0.088 g DW) → 105 / 91 / 167 / 175 / 166 / 208. Default (factor off) at 5 %: see CROP-003. Exploratory model check from 02.09 (open-channel light, TMY temperature, 0.088 g DW start): default model (no temperature factor) 1.85 g on 18.09 and 4.80 g on 25.09; with the exploratory TEMP-001 factor 1.26 and 3.17 g; measured 0.29 and 1.08 g, i.e. early growth about 4–6× too fast (3–4× with the factor). Not acted on (single unfinished cycle; bed light channel unmapped)
- Reproduction command and output: `simulate_growth_timeseries` from 2026-09-02 12:00 with the derived initial state

## Decision log

- Decision: Use the measured fresh seedling mass (0.90 g) as the transplant state for all cycles; derive dry mass with the output dry-matter fraction; keep later weighings as preliminary evidence only
- Rationale: The seedling stage is managed consistently and is representative across the year; growth weighings from one unfinished cycle are not
- Date: 2026-10-13
- Follow-up needed: (1) weigh a pooled seedling sample (e.g. 20 seedlings) on a 0.01 g or better scale, dried at 65–70 °C to constant mass, to measure seedling dry matter; (2) add the cycle-1 harvest weighing; (3) repeat transplant weighings each cycle (workflow: Anara skill `lettuce-seedling-weighing`)
