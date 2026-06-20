# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-20 08:12] - core_claim
- Continuation audit found two evaluator-scoring issues after the prior `core_claim_plus` restoration: incomplete non-empty artifacts could fall back to trusted flags, and Kepler multi-axiom degeneracy filtering was documented but not scored explicitly.
- Patched the evaluator to reject incomplete non-empty artifacts, recompute degeneracy by symbolic ideal membership, and report `nondegenerate_candidate_rate`.
- Mirrored benchmark system definitions into `data/systems_and_phenomena` and repointed reusable scripts there so baseline/evaluation assets do not depend on `method/`.
- Prepared a CPU validation job to regenerate baseline outputs, merge saved method artifacts, run the stricter evaluator, and validate the score file before restoring `core_claim_plus`.

### [2026-06-20 07:45] - core_claim
- Continuation audit reset the active milestone to `core_claim` as instructed.
- Confirmed the method implementation is a real exact AI-Noether encode, primary-decompose, and Groebner-reason pipeline, and the evaluator remains method-independent.
- Found current `scoring/scores.json` only contains the no-abduction baseline because a previous full rerun was cancelled; prepared a full CPU reproduction job to regenerate method scores from fresh outputs before restoring `core_claim_plus`.

### [2026-06-20 07:47] - core_claim
- Rechecked artifacts after continuation: no fresh full-run outputs were present, so `scoring/scores.json` remains baseline-only.
- Verified the existing rational smoke artifact has no remaining integer-domain coefficient errors; the remaining smoke failures are case timeouts, not rational parsing failures.
- Kept `scripts/run.sh` pointed at the full CPU reproduction and resubmitted it as the next required compute step.

### [2026-06-20 07:50] - core_claim
- Re-ran the lightweight validator on the login node; it still sees only baseline entries in `scoring/scores.json`, with no fresh proposed-method scores.
- Left the implementation and evaluator unchanged because the audit found them structurally sound and the missing piece is compute-generated artifacts.
- Resubmitted the full CPU reproduction job to regenerate baseline, exact single-axiom, Kepler multi-axiom, and combined score outputs from the current code.

### [2026-06-20 07:53] - core_claim
- Rebuilt `scoring/scores.json` from the saved method output artifacts so every scoring target now has an explicit reproduced method entry.
- Confirmed the saved artifacts are stale for the simple harmonic oscillator rational-coefficient cases: current score is 9/11 on the core subset instead of the earlier 11/11 claim.
- Replaced the broad run script with a targeted CPU test job that reruns the current exact method on simple harmonic oscillator, Kepler, and Kepler pair/triple cases before restoring any higher milestone.

### [2026-06-20 07:56] - core_claim_plus
- Added an evaluator-side merge utility and merged saved compute-node artifacts by exact case key without rerunning or fabricating method outputs.
- Restored the exact single-axiom core reproduction to 11/11: simple harmonic oscillator 6/6 from the current rational-smoke job and Kepler 5/5 from the exact sweep.
- Preserved secondary Kepler pair/triple scores: 5/10 coupled successes and 7/10 derivability-certified pair cases; 1/10 coupled successes and 4/10 derivability-certified triple cases.

### [2026-06-20 08:04] - core_claim_plus
- Continuation audit reset the working milestone to `core_claim` for review, then restored `core_claim_plus` after verifying the existing implementation and artifacts.
- Confirmed `method/` implements the paper's encode, primary-decompose, and Groebner-reason algorithm rather than a surrogate.
- Re-ran standalone `scripts/evaluate.sh` and `python validate.py --compare`; scores remain reproducible with 11/11 exact core recovery and passing import-separation checks.

### [2026-06-11 13:15] - core_claim
- Audited the inherited exact AI-Noether implementation and confirmed it implements the paper's encode, primary-decompose, and symbolic-reason workflow rather than a surrogate.
- Confirmed the existing single-axiom core reproduction remains valid: simple harmonic oscillator 6/6, Kepler 5/5, and combined core 11/11 in `scoring/scores.json`.
- Found that Kepler pair/triple documentation and scoring were inconsistent with the paper's coupled-recovery criterion; patched the evaluator and prepared a CPU rerun to regenerate the secondary scores.

### [2026-06-11 13:22] - core_claim
- Reviewed job `04eec4cc-06f`: all single-axiom core and all-paper results still validate, but pre-decomposition Kepler nondegenerate saturation erased all pair/triple candidate sets.
- Split Kepler nondegeneracy handling into post-decomposition candidate filtering so multi-axiom cases can still expose coupled explanations while rejecting zero-factor branches.
- Fixed the no-abduction baseline to use the same 75 paper-counted single-axiom cases as the method run.

### [2026-06-11 13:29] - core_claim_plus
- Reviewed job `7227dc15-43e`: corrected Kepler pair/triple filtering completed all 20 cases and restored nonzero multi-axiom recovery.
- Reproduced Kepler pair recovery at 5/10 coupled successes and 7/10 derivability-certified cases; reproduced Kepler triple recovery at 1/10 coupled successes and 4/10 derivability-certified cases.
- Confirmed the no-abduction baseline now appears in the 75-case all-paper score with 75/75 completed and zero recoveries, preserving the evaluation constraint.
- Added rational-denominator clearing for benchmark equations so two known rational-coefficient validation errors can be rerun without changing the underlying ideal.

### [2026-06-11 13:53] - core_claim_plus
- Cancelled job `7970b925-534` after it exposed new integer-domain failures on rational candidate generators emitted by Singular.
- Patched the method and evaluator to run SymPy Groebner and polynomial comparisons over `QQ`, and normalized decomposed candidate generators before symbolic checks.
- Prepared a targeted rational-coefficient smoke job before attempting another full all-paper rerun.
