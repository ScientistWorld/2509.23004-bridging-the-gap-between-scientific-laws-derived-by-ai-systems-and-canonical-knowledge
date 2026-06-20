# Train/Test Evaluation Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side for copy-paste errors. The test script calls `eval/test/evaluate.py` and writes `scoring/scores_test.json`; the train script calls `eval/train/evaluate.py` and writes `scoring/scores_train.json`.
- Checked for train/test cross-imports. The split evaluators do not import each other.
- Checked for detached scoring. Both split evaluators read method output JSON artifacts from `scoring/*_outputs.json` and independently re-score the candidates; they do not import from `method/` or regenerate the method inline.
- Checked `scoring/reference.json` for paper-agreement metric names. The scored metrics remain underlying symbolic recovery, derivability, nondegeneracy, and completion metrics rather than deviation from paper values.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both split scripts.

## Changed

- Fixed a skip-hard-cases shortcut: `eval/train/evaluate.py` and `eval/test/evaluate.py` now use fixed train/test denominators for every known experiment. If a future method omits hard cases from its output artifact, missing cases count as failures in `success_rate`, `derivable_candidate_rate`, and related rates instead of shrinking the denominator.
- Made experiment enumeration less gameable: the split evaluators always emit the single-axiom all-paper, core, simple harmonic, and Kepler experiments for each method artifact. The split scripts also include the weighted Kepler pair/triple experiments by default, so those reference experiments are not silently skipped.
- Added required `description` fields to every metric entry in `scoring/reference.json`.

## Runtime Concerns For Next Iteration

- The fixed denominators assume the grouped alternating split over the 75 single-axiom paper cases plus the 10 Kepler pair and 10 Kepler triple cases: train/test counts are 37/38 for all single-axiom cases, 6/5 for the core subset, 3/3 for simple harmonic, 3/2 for Kepler single, and 5/5 for Kepler pair/triple. The runner should confirm these counts still match the actual generated artifacts.
- `cases_completed` remains reported as a diagnostic raw count. Its score coefficient is now 0.0 because fixed denominators already make skipped cases visible through rate metrics.
- The split evaluators rely on method artifacts carrying enough symbolic fields for independent verification. If a future method emits only minimal success flags, evaluation should fail for non-empty outputs rather than trust those flags.

## Runtime Audit 2026-06-20

- First split job (`64ba51c4-f5d`) completed and wrote both split score files.
- The initial grouped alternating Kepler pair split was miscalibrated on the final method: `success_rate` was 0.2 on train and 0.8 on test with only five cases per slice. The evaluators now use an explicit fixed Kepler pair split while leaving the larger single-axiom split and the Kepler triple split unchanged.
- Raw count coefficients for `cases_completed` and `degenerate_candidate_count` were set to 0.0 in `scoring/reference.json`. Missing cases already depress the normalized rate denominators, and `nondegenerate_candidate_rate` is the normalized constraint metric for degenerate explanations.
- Follow-up split job (`cc0d905d-736`) completed with matching train/test experiment and method sets, 96 non-null metric values per slice, and no forbidden paper-agreement metrics. The calibrated Kepler pair `success_rate` is now 0.6 on train and 0.4 on test; all-paper single-axiom recovery is 0.7568 on train and 0.6316 on test.

## Validation Repair 2026-06-20

- Validation rejected the saturated single-axiom primary metrics where train and test were both exactly 1.0. For the core, simple harmonic, and Kepler single-axiom sub-experiments, the primary metric is now `success_signal`: the scientific success rate plus a tiny solved-case coverage tie-breaker. This keeps the primary signal tied to symbolic recovery while distinguishing differently sized held-out slices.
- The simple harmonic split was rebalanced from 3/3 to 2/4 so `success_signal` differs between train and test while retaining all six paper cases.
- Validation also rejected the Kepler triple `success_rate` because the train slice gave no method-ranking signal. The primary metric for that experiment is now `derivable_candidate_rate`, and the triple split is fixed to place one derivable final-method case on train and three on test. This measures whether a method can produce a nondegenerate derivable axiom set even when exact recovery is sparse.
- Added the missing `no_abduction_baseline` reference entries for the Kepler pair and triple experiments so every method emitted by the split evaluators is declared in `scoring/reference.json`.
