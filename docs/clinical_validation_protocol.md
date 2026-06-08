# Clinical Validation Protocol

## Purpose

Before public release, PHTA triage outputs must be validated against known clinical cases to ensure safety and accuracy.

## Methodology

1. Compile 500+ clinical cases with known correct triage levels (1-4)
2. Each case includes: chief complaint, symptom description, relevant history
3. Cases reviewed by licensed physician for correct triage assignment
4. Run PHTA on all cases, record output triage level
5. Compare PHTA output vs. clinical standard

## Metrics

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Overall accuracy | ≥ 85% | < 80% triggers investigation |
| False negative rate (emergencies) | 0% | ANY false negative blocks release |
| False negative rate (urgent) | < 5% | > 10% triggers investigation |
| Red flag detection | 100% | ANY red flag fixture failure blocks merge |

## Validation Schedule

- **Pre-release:** Full 500-case validation
- **Monthly:** Random audit of 50 triage decisions
- **Quarterly:** Re-run full validation set
- **On rule change:** Re-run all fixtures affected by changed rule

## Case Sources

- Public clinical vignette datasets
- Standardized patient scenarios
- MIMIC-III chief complaints (de-identified)
- Vietnam-specific cases curated with clinical advisor
- Synthetic cases for rare but critical presentations

## Reviewer Requirements

- Licensed physician (MD or equivalent)
- Preferably emergency medicine, family medicine, or internal medicine
- Vietnam-licensed for local disease context
- Reviews all red flag definitions and triage rules
