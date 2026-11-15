# Scoring Targets

Scores come from `scoring/scores_test.json` (hidden test) and
`scoring/scores_train.json` (visible train); the reference rows are those of
`ai_noether_exact`. Coefficients and weights are in `scoring/reference.json`.

## single_missing_axiom (weight 0.30)

* Primary: maximize `recovery_rate` (coefficient 1.0).
* Secondary benefits: `top1_success_rate` (0.3), `explanation_rate` (0.25).
* Constraint: keep `unsound_rate` low (0.3, lower is better); failed runs count here
  and as zero in every benefit metric.
* Reference (held out, 64 instances): recovery 1.000, explanation 1.000, top-1 0.828,
  unsound 0.344.

## two_missing_axioms (weight 0.25)

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefit: `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).
* Diagnostic only: `recovery_rate` (decoupled recovery of both laws; 0 for every
  honest method on the held-out slice, coefficient 0).
* Reference (held out, 55 instances): explanation 0.655, top-1 0.600, unsound 0.145.

## three_missing_axioms (weight 0.20)

* Primary: maximize `explanation_rate` (1.0).
* Secondary benefit: `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).
* Diagnostic only: `recovery_rate` (coefficient 0).
* Reference (held out, 40 instances): explanation 0.300, top-1 0.275, unsound 0.075.

## multiple_consequences (weight 0.25)

* Primary: maximize `recovery_rate` (1.0): one set recovers every removed axiom.
* Secondary benefit: `top1_success_rate` (0.3).
* Constraint: keep `unsound_rate` low (0.3).
* Diagnostic only: `explanation_rate`, `axiom_recovery_rate` (equal to
  `recovery_rate` on these identifiable instances; coefficient 0).
* Reference (held out, 59 instances): recovery 0.864, top-1 0.864, unsound 0.000
  (by number of removed axioms: 27/28, 16/19, 4/6, 4/6).

Baselines on the held-out slice: `enumerative_baseline` recovers 0.438 of single
removals, explains 0.091 / 0.050 of two- / three-axiom removals and recovers none
of the multiple-consequence instances; `no_abduction_baseline` scores zero on
every benefit metric.

Train slice reference (the paper's theories): single recovery 1.000 (top-1 0.845,
unsound 0.466), two-axiom explanation 0.500, three-axiom 0.394,
multiple-consequence recovery 0.857.

Paper-reported values (on the paper's twelve theories, 7200 s timeout) are kept
under `_paper_reported` in `scoring/reference.json`: 73/75 single-axiom
recoveries, 105/215 two-axiom and 109/383 three-axiom coupled recoveries, exact
decoupled recovery of three removed axioms from three consequences on the
relativistic-laws theory (Section 3.3); the paper's LLM and cvc5 baselines solve
none.
