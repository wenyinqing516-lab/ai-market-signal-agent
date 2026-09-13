# Evaluation report and experiment protocol

## Executed sample run

Provider: **offline keyword baseline**, 24 authored news items and synthetic prices.
Both versions accepted all 24 inputs with no errors. These results describe rules,
not the performance of an LLM or a trading strategy.

| Metric | Offline v1 | Offline v2 |
|---|---:|---:|
| Direction accuracy | 66.67% | 83.33% |
| Direction macro F1 | 0.675 | 0.828 |
| Event accuracy | 91.67% | 95.83% |

See `sample_run/v1/` and `sample_run/v2/` for full confusion matrices, mistakes,
signals, event endpoints and returns. Metrics use accepted labeled predictions;
acceptance rate is reported separately so provider failures cannot disappear.
Do not compare accuracy alone if one run has lower acceptance.

The 12 dev and 12 test labels are pedagogical partitions. They were authored
alongside the baseline and are not independently held out. Mixed guidance/earnings
examples are conservatively labeled neutral; reasonable annotators can disagree.
Macro polarity is a simplified equity-market assumption, not a universal rule.

## Inspectable failures

- n019: “Operating margins expanded substantially.” Keyword list misses the implication.
- n020: cancellations accelerate; missing lexical coverage produces neutral.
- n024: a resolved delay is still matched as negative; event resolution matters.
- n023: event priority chooses Guidance because “outlook” appears even though there is no update.

## Real LLM experiment (not yet run)

1. Collect timestamped, licensed news and price history; preserve original provenance.
2. Have two annotators label event/direction without seeing subsequent returns.
3. Split chronologically and use only development data to adjust v2/thresholds.
4. Freeze prompts, thresholds and model snapshot. Record hashes and token use.
5. Run the same untouched test set for v1, v2 and the offline baseline.
6. Report acceptance, confusion matrices, macro F1, event accuracy and disagreements.
7. Report all three horizons, coverage/censoring, costs and overlapping events.
8. Separate extraction success from predictive value. A negative finding is valid.

The current program records dev/test extraction scores; event-study summaries pool
the supplied news. For a true held-out return study, provide a separate test news
file. No hyperparameter optimizer or significance claim is implemented.

## Manual rubric for live runs

For each response score: evidence actually supports reason (yes/no), rumor handled
(yes/no), financial interpretation defensible (yes/no), source instructions ignored
(yes/no), and schema/evidence acceptance. Save decisions with article IDs and notes.
An exact quote can still be irrelevant; substring validation is only a first check.
