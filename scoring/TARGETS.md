# Scoring Targets

Scores come from `scoring/scores_test.json` (hidden test) and
`scoring/scores_train.json` (visible train); the reference rows are those of
`ai_noether_exact`. Coefficients and weights are in `scoring/reference.json`.

## single_missing_axiom

* Primary: maximize `recovery_rate` (coefficient 1.0).
* Secondary benefits: `top1_success_rate` (0.3), `explanation_rate` (0.25).
* Constraint: keep `unsound_rate` low (0.3, lower is better); failed runs count here
  and as zero in every benefit metric.

## two_missing_axioms

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefits: `recovery_rate` (0.5), `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).

## three_missing_axioms

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefits: `recovery_rate` (0.5), `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).

Paper-reported values (on the paper's twelve theories, 7200 s timeout) are kept
under `_paper_reported` in `scoring/reference.json`: 73/75 single-axiom
recoveries, 105/215 two-axiom and 109/383 three-axiom coupled recoveries; the
paper's LLM and cvc5 baselines solve none.
