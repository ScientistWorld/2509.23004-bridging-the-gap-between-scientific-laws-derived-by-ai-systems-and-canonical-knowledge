# Scoring Targets

Future agents should optimize symbolic recovery of missing polynomial axioms while preserving derivability guarantees.

## exact_single_axiom_core

Primary target: maximize `success_rate` on the combined 11 single-axiom cases from simple harmonic oscillator and Kepler.

Constraint targets:

- `strong_success_rate` should remain high, showing that candidates recover the canonical missing relation rather than any unrelated shortcut.
- `cases_completed` should equal the number of benchmark cases, showing that gains are not achieved by silently skipping hard cases.

## simple_harmonic_single_axiom

Primary target: recover all 6 single missing axioms in the simple harmonic oscillator system.

Constraint targets: maintain `strong_success_rate` and complete all 6 cases.

## kepler_single_axiom

Primary target: recover all 5 single missing axioms in the Kepler system.

Constraint targets: maintain `strong_success_rate` and complete all 5 cases.
