# Scoring Targets

Scores come from `scoring/scores_test.json` (hidden test) and
`scoring/scores_train.json` (visible train); the reference rows are those of
`ai_noether_exact`. Coefficients and weights are in `scoring/reference.json`.

## single_missing_axiom (weight 0.40)

* Primary: maximize `recovery_rate` (coefficient 1.0).
* Secondary benefits: `top1_success_rate` (0.3), `explanation_rate` (0.25).
* Constraint: keep `unsound_rate` low (0.3, lower is better); failed runs count here
  and as zero in every benefit metric.
* Reference (held out): recovery 1.000, explanation 1.000, top-1 0.844, unsound 0.344.

## two_missing_axioms (weight 0.35)

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefit: `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).
* Diagnostic only: `recovery_rate` (decoupled recovery of both laws; 0 for every
  honest method on the held-out slice, coefficient 0).
* Reference (held out): explanation 0.655, top-1 0.600, unsound 0.145.

## three_missing_axioms (weight 0.25)

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefit: `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).
* Diagnostic only: `recovery_rate` (coefficient 0).
* Reference (held out): explanation 0.300, top-1 0.275, unsound 0.050.

Baselines on the held-out slice: `enumerative_baseline` recovers 0.438 of single
removals and explains 0.091 / 0.050 of two- / three-axiom removals;
`no_abduction_baseline` scores zero on every benefit metric.

Paper-reported values (on the paper's twelve theories, 7200 s timeout) are kept
under `_paper_reported` in `scoring/reference.json`: 73/75 single-axiom
recoveries, 105/215 two-axiom and 109/383 three-axiom coupled recoveries; the
paper's LLM and cvc5 baselines solve none.
