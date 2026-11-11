# Constraints

* A method is a solver script `scripts/solvers/<name>.sh <instance.json> <output.json>`
  that writes `{"candidate_sets": [[poly, ...], ...]}`. It must finish within
  `ABDUCTION_TIME_LIMIT` seconds per instance; the evaluator kills it otherwise.
* At most five candidate sets are considered, each with at most `num_missing`
  polynomials. Exact polynomials only (integers, variables, `+ - * ^`,
  parentheses, division by integer constants).
* The evaluator, the instances, the time limit, the candidate budget and all
  ground truth are fixed by `eval/`. Do not modify `eval/`, the instance files,
  or the scoring files; scores written anywhere else are not read.
* Do not read evaluator files (`eval/`, instance files, cached outputs, or their
  copies in the repository history) from a solver, and do not hardcode benchmark
  laws, removed axioms or reference outputs.
  The held-out theories are not available to methods.
* Proposed axioms must be justified by the instance itself; the evaluator checks
  them against the complete theory, so contradictions, zero-forcing laws, copies
  of the target and restatements of known axioms earn nothing or are penalized.
* No training data exists for the missing axioms; methods that need training
  must train on the visible slice only.
* Keep `eval/` free of imports from `method/`; solvers may use any code under
  `method/`, `baseline/` or new directories.
