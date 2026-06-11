# Problem Definition

The benchmark is polynomial abductive inference for scientific theories. Each instance provides:

- a finite set of background polynomial equations treated as known axioms,
- one or more polynomial target hypotheses, and
- a deliberately incomplete axiom set produced by removing one or more required axioms.

The task is to propose additional polynomial equations which, when added to the incomplete axiom set, make the target hypothesis algebraically derivable. A candidate succeeds only if it is not merely numerically correlated with the target but actually closes the logical gap between the incomplete theory and the target relation.

The core setting reproduced here is exact symbolic recovery with one missing axiom on two benchmark physical systems:

- simple harmonic oscillator, with 6 single-axiom removal cases;
- Kepler/orbital dynamics, with 5 single-axiom removal cases.

Inputs and outputs are symbolic polynomial strings, not sampled data. Evaluation must be independent of any particular implementation: a future method may use a different search strategy as long as it writes the same output format for recovered candidates.
