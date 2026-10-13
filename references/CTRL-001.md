# CTRL-001 — Controller objective weights and operating-point evidence

## Citation

- Authors / organization: AgriPV Digital Twin Prototype project
- Year: 2026
- Full title: Controller tuning weights and sensitivity scenario
- Journal / publisher / report: Project methods record
- Volume, issue, pages: Not applicable
- DOI or stable URL: Not applicable
- Local source file (if retained): [`project/scenarios/run_timeseries.py`](../project/scenarios/run_timeseries.py)
- Access date: 2026-10-13

## Source and scope

- Source type: Engineering tuning assumptions and scenario benchmark
- Site, cultivar, equipment, and study scale: Configured AgriPV controller
  and the bundled 2026 weather scenario
- What was measured or derived: Scalar PV-loss and movement weights in the
  objective and the code's sensitivity-sweep design.
- Relevant page, table, figure, equation, or dataset fields: Defaults in
  `run_timeseries_pipeline`; axes in `run_sensitivity_sweep` in
  `project/scenarios/run_benchmark.py`.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Checked-in defaults `pv_loss_weight`, `movement_weight` | `run_timeseries_pipeline` signature | Mixed normalized objective terms | 1.0, 0.0 | Current code defaults; not the 0.001/0.05 pair described in an earlier review note |
| Sensitivity candidates | `run_sensitivity_sweep` defaults | DLI targets/limits and normalized weights | targets 10/14; ceilings 18/24; PV weights 0.5/1.0; movement weights 0/0.05 | Implemented grid; a full annual run/output was not found in the repository |
| Reported benchmark trade-off | Supplied project review note | Relative PV energy and DLI | PV −12% for DLI +10% | Reported but not reproduced from a retained benchmark artifact in this update |

## Connection to this project

- Reference ID and evidence role: CTRL-001; model-tuning record, not a
  literature parameter or calibrated optimum
- Code file and symbol: [`project/scenarios/run_timeseries.py`](../project/scenarios/run_timeseries.py),
  `run_timeseries_pipeline`; [`project/scenarios/run_benchmark.py`](../project/scenarios/run_benchmark.py),
  `run_sensitivity_sweep`
- Configuration key(s): Function arguments `pv_loss_weight`, `movement_weight`
- Related test(s): [`project/tests/test_benchmark.py`](../project/tests/test_benchmark.py)
- Adaptation made for this project: The optimizer's candidate weights are
  normalized in the current implementation; historical raw-unit weights are
  not considered equivalent.
- Known differences or limitations: No derivation establishes a universal
  optimal weight. The reported PV/DLI trade lacks a retained run identity and
  output for independent reproduction.

## Validation record

- Dataset identity and version: Bundled 2026 field dataset/scenario; exact
  full-sweep output not retained
- Calibration or independent validation: Not calibrated against field
  outcomes
- Inclusion/exclusion and quality-control rules: Benchmark masks incomplete
  daily coverage as implemented in the pipeline
- Metrics and uncertainty method: DLI, covered PV energy, and movement
  metrics; no uncertainty interval
- Results and unresolved discrepancies: The review-reported −12%/+10% trade
  is treated as a provisional observation, not independently checked here.
- Reproduction command and output: `python -m project.scenarios.run_benchmark
  --sensitivity`; retain the generated output and code/data revision for a
  verifiable result.

## Decision log

- Decision: Keep the current defaults (PV weight 1.0, movement weight 0.0)
  explicitly provisional; do not rewrite the review's 0.001/0.05 as current
  code defaults.
- Rationale: The actual checked-in code and implemented sweep differ from
  the older stated pair, and no retained full-sweep result substantiates a
  selected optimum.
- Date: 2026-10-13
- Follow-up needed: Run and retain the full annual target/ceiling/weight sweep,
  reproduce the claimed PV −12% / DLI +10% trade-off, and compare results
  across coverage and sensitivity assumptions before selecting defaults.
