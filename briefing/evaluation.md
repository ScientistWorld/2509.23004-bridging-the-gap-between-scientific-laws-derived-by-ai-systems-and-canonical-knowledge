# Evaluation Protocol

Evaluation reads candidate-output artifacts passed to `scripts/evaluate.sh`, or compatible default JSON artifacts in `scoring/`. It does not import from `method/` and does not rerun candidate generation.

Each case is scored from saved candidate axiom sets. For single-missing-axiom cases, success requires recovering the removed canonical axiom while passing symbolic derivability checks for the target. For multi-missing-axiom cases, success follows the paper's coupled-recovery setting: a candidate may be entangled rather than a literal copy of every removed axiom, but it must be nondegenerate and make the target derivable. The main metric is `success_rate`, the fraction of benchmark cases solved. `derivable_candidate_rate` records whether each case produced any derivability-certified candidate, and `cases_completed` records how many cases ran to normal completion rather than timing out or failing.

The reproduced experiments are:

- `exact_single_axiom_core`: all 11 single-axiom cases from simple harmonic oscillator and Kepler.
- `exact_single_axiom_all_paper`: all 75 single-axiom cases reported in the paper's Appendix D.1 / Table 6.
- `simple_harmonic_single_axiom`: 6 single-axiom cases for the simple harmonic oscillator.
- `kepler_single_axiom`: 5 single-axiom cases for Kepler.
- `kepler_pair_axiom`: 10 two-missing-axiom cases for Kepler from Table 2.

The three-missing-axiom Kepler setting is present only as an opt-in diagnostic artifact. It is not part of the official `scores.json` target set because the checked-in reproduction does not yet match the paper's reported count on that setting.

The paper reports 6/6 and 5/5 success for these two single-axiom systems, so the core reference target is 11/11. A no-abduction baseline that returns no candidates scores 0/11 and is included to validate that the evaluator is measuring recovered explanations rather than simply counting completed cases.
