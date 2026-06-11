# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-06-11 12:49] - core_claim_plus
- Validated the exact AI-Noether symbolic abduction environment with `python validate.py --compare`.
- Reproduced the core exact single-axiom claim on simple harmonic oscillator and Kepler: 11/11 recoveries.
- Expanded beyond the minimum to the paper-counted 75 exact single-axiom cases: 57/75 canonical recoveries and 62/75 derivable-candidate cases under the compact timeout.

### [2026-06-11 12:54] - core_claim_plus
- Audited the inherited workspace and confirmed the implementation follows the paper's exact encode, primary-decompose, and reason algorithm.
- Strengthened the evaluator so new outputs are symbolically rescored outside `method/`.
- Prepared a CPU job for the Kepler pair/triple missing-axiom experiments from Table 2.

## Stop Justification
- Not stopped: submitting Kepler multi-axiom secondary experiment.
