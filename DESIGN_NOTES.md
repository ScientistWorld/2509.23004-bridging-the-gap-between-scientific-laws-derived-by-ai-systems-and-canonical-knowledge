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
- `cases_completed` is still a raw count metric, inherited from the first pass. The new fixed denominators make skipping visible through rate metrics, but the next runner should watch that the scoring aggregator does not let raw completion counts dominate rate-based scientific metrics.
- The split evaluators rely on method artifacts carrying enough symbolic fields for independent verification. If a future method emits only minimal success flags, evaluation should fail for non-empty outputs rather than trust those flags.
