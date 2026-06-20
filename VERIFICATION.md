# Verification Report

## Initial Assessment

The workspace entered final verification at `core_claim_plus`. The claimed milestone remains justified: the official scores show full recovery on the 11-case exact single-axiom core subset, a zero no-abduction baseline, and an additional Kepler two-axiom result beyond the core claim. The method/evaluation separation is intact, and `python validate.py --compare` passes after the fixes below.

## Issues Found

- Critical: the top-level evaluator was using only emitted cases as the denominator for success rates. This let incomplete artifacts inflate results by omitting failed or timed-out cases.
- Critical: `scoring/reference.json` contained reproduced partial values for the all-paper proposed row instead of the paper-reported 73/75 exact recovery result.
- Minor: `scores.json` was missing the same `success_signal` tie-break metric used by the reference schema for some experiments.
- Minor: method-agnostic documentation and `scripts/download.sh` contained unnecessary method-name wording in places visible to from-scratch users.
- Minor: `scripts/evaluate.sh` cannot recompute non-empty symbolic artifacts under the login-node Python because SymPy is not installed there. The packaged container installs SymPy via `environment/setup.sh`, so this is not a gym blocker.

## Fixes Applied

- Updated `eval/evaluate_exact.py` so official experiments use fixed expected totals when summarizing cases. Missing cases now count against the denominator.
- Restored the all-paper proposed reference result to the paper-reported 73/75 value and regenerated the checked-in reproduced summary values with corrected denominators.
- Added `success_signal` consistently to the reproduced score summaries so scored metrics match the reference schema.
- Reworded the method-agnostic evaluation briefing and download script messages to avoid leaking the paper method.
- Marked unremovable root metadata bind artifacts (`README.md`, `manifest.json`) as local skip-worktree entries; repository HEAD still carries the normal text files, and they are not part of the gym artifacts.
- Re-ran `python validate.py --compare`; all scoring, import-separation, train/test, and shared-path checks pass.

## Final Judgment

The workspace is ready to serve as a research gym. From-scratch agents can use the problem definition, data assets, and evaluator without importing method code. Improve-mode agents have the reproduced method, baseline artifacts, reference scores, and documentation needed to iterate. The scoring now penalizes incomplete output artifacts instead of rewarding selective omission.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: high
- Key limitation: the full 75-case exact sweep is partial; Kepler three-axiom recovery remains diagnostic rather than an official score target.
