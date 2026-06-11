# Experiments

## exact_single_axiom_core

This experiment asks whether a method can solve all single-missing-axiom cases in the selected core benchmark subset. It combines the simple harmonic oscillator and Kepler systems to give 11 cases. Success means the output candidates make the target relation derivable from the incomplete background theory.

## simple_harmonic_single_axiom

This experiment isolates the 6 single-missing-axiom cases from the simple harmonic oscillator system. It provides a compact sanity check for exact symbolic recovery.

## exact_single_axiom_all_paper

This experiment sweeps the 75 single-missing-axiom cases reported in the paper's detailed appendix table. It is the broader single-axiom reproduction target beyond the two-system core subset.

## kepler_single_axiom

This experiment isolates the 5 single-missing-axiom cases from the Kepler system. It is a second exact symbolic benchmark with a different physical domain.

## kepler_pair_axiom

This experiment evaluates all 10 two-missing-axiom cases from the Kepler system. It tests whether a method can recover coupled explanatory relations when the incomplete theory lacks more than one axiom.

## kepler_triple_axiom

This experiment evaluates all 10 three-missing-axiom cases from the Kepler system. It is a harder multi-axiom recovery setting where the paper reports only partial recovery.

## no_abduction_baseline

The baseline emits no candidate axioms. It should score zero on recovery metrics while completing all cases, which helps confirm that the evaluator rewards explanatory candidates rather than file presence or case enumeration.
