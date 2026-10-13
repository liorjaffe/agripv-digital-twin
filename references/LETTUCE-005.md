# LETTUCE-005 — Sakamoto and Suzuki hydroponic lettuce study

## Citation

- Authors / organization: Masaru Sakamoto and Takahiro Suzuki
- Year: 2015
- Full title: *Effect of Root-Zone Temperature on Growth and Quality of Hydroponically Grown Red Leaf Lettuce (Lactuca sativa L. cv. Red Wave)*
- Journal / publisher / report: *American Journal of Plant Sciences*
- Volume, issue, pages: 6(14), 2350–2360
- DOI or stable URL: <https://doi.org/10.4236/ajps.2015.614238>;
  [publisher full text](https://www.scirp.org/journal/paperinformation?paperid=59655);
  [PDF](https://content.scirp.org/pdf/ajps_2015091616560642.pdf)
- Local source file (if retained): Not retained
- Access date: 2026-10-13

## Source and scope

- Source type: Peer-reviewed primary research
- Site, cultivar, equipment, and study scale: Hydroponically grown red-leaf
  lettuce cultivar ‘Red Wave’; seven-day root-zone-temperature experiment
  starting at 22 days after sowing, using deep-flow technique.
- What was measured or derived: Top and root fresh/dry weights across four
  root-zone temperature treatments; a root share can be derived from reported
  treatment means.
- Relevant page, table, figure, equation, or dataset fields: Table 2;
  article pages 2350–2360. The exact printed page containing Table 2 was not
  independently identified.

## Evidence extracted

| Claim or value | Source location | Original unit | Normalized value/unit | Uncertainty / qualification |
| --- | --- | --- | --- | --- |
| Top and root dry weights by treatment | Table 2, means ± SE, n=6 | mg | Top/root: 211/36 at 10 °C; 253/44 at 20 °C; 251/38 at 25 °C; 233/35 at 30 °C | Specific to ‘Red Wave’ and this short experiment |
| Derived root share by treatment | Calculated from Table 2 means: root/(top + root) | Fraction of top-plus-root dry mass | 0.146, 0.148, 0.131, 0.131; mean ≈0.139 | Ratio of treatment means, not a reported model parameter or an individual-plant mean |
| Top dry-matter fraction | Table 2 fresh and dry weights | Fraction of fresh mass | Approximately 5.5–6.8% across treatments | Derived from treatment means; not a curly-lettuce range |
| Combined top-plus-root dry-matter fraction | Table 2 fresh and dry weights | Fraction of combined fresh mass | Approximately 5.3–6.6% across treatments | Derived from treatment means; not a general crop recommendation |

## Connection to this project

- Reference ID and evidence role: LETTUCE-005; hydroponic primary-study
  comparison evidence, not a site measurement
- Code file and symbol: [`project/models/lettuce.py`](../project/models/lettuce.py),
  `LettuceParams.c_tau`
- Configuration key(s): Not applicable
- Related test(s): [`project/tests/test_validation.py`](../project/tests/test_validation.py)
- Adaptation made for this project: `c_tau` is set to 0.14 as a rounded
  proxy based on the mean of Table 2's treatment root shares.
- Known differences or limitations: ‘Red Wave’ is not the project's curly
  ‘Crespa’; the study's root/top pools are not identical to the model's
  structural-biomass allocation pools.

## Validation record

- Dataset identity and version: Sakamoto & Suzuki (2015), Table 2
- Calibration or independent validation: Not calibrated to the UFSC site
- Inclusion/exclusion and quality-control rules: Ratios calculated from
  published treatment means only
- Metrics and uncertainty method: No uncertainty propagated for ratio of means
- Results and unresolved discrepancies: Table means support a root share of
  approximately 0.13–0.15 for this cultivar/experiment; they do not establish
  the UFSC cultivar's value.
- Reproduction command and output: For each treatment,
  `root_dry_weight / (top_dry_weight + root_dry_weight)`.

## Decision log

- Decision: Use `c_tau = 0.14` as the provisional hydroponic-model proxy,
  replacing the soil-attributed 0.15 in the default parameter.
- Rationale: Table 2 gives a derived mean root share near 0.14 for a
  hydroponic lettuce study. This is a better system-context match than the
  soil-lettuce attribution, but is not a Crespa/site calibration.
- Date: 2026-10-13
- Follow-up needed: Verify the exact printed page for Table 2 and obtain
  transplant/top/root dry-mass observations for the UFSC Crespa cultivar;
  test sensitivity around 0.14 before relying on quantitative biomass
  predictions.
