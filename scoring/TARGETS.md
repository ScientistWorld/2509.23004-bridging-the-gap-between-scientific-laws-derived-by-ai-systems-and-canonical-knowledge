# Scoring Targets

Future agents should optimize symbolic recovery of missing polynomial axioms while preserving derivability guarantees.

## exact_single_axiom_all_paper

Primary target: maximize `success_rate` over the 75 single-axiom removal cases reported in the paper.

Constraint targets:

- `derivable_candidate_rate` should remain high, showing that successful cases include candidates that actually derive the target relation.
- `cases_completed` should equal 75, showing that gains are not achieved by skipping hard cases.

## exact_single_axiom_core

Primary target: maximize `success_rate` on the combined 11 single-axiom cases from simple harmonic oscillator and Kepler.

Constraint targets:

- `derivable_candidate_rate` should remain high, showing that successful cases include candidates that actually derive the target relation.
- `cases_completed` should equal the number of benchmark cases, showing that gains are not achieved by silently skipping hard cases.

## simple_harmonic_single_axiom

Primary target: recover all 6 single missing axioms in the simple harmonic oscillator system.

Constraint targets: maintain `derivable_candidate_rate` and complete all 6 cases.

## kepler_single_axiom

Primary target: recover all 5 single missing axioms in the Kepler system.

Constraint targets: maintain `derivable_candidate_rate` and complete all 5 cases.

## Diagnostic Not Currently Scored

The Kepler pair/triple missing-axiom Table 2 sweep has been run and documented in `PROGRESS.md`, but it is not a formal scoring target in this gym because the compact reproduction does not yet match the paper's reported multi-axiom results. Future agents can opt into diagnostic scoring with `python eval/evaluate_exact.py --include-multi ...` after improving the coupled-relation selection procedure enough for the results to be numerically consistent with the paper.
