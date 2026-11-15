# Research Direction

This gym studies automated abductive inference for scientific laws written as
polynomial equations: recover the axioms missing from a theory, given the rest of
the theory and one or more observed laws, with formal derivability.

Productive directions:

* recovering the missing laws exactly when several of their consequences are
  observed, especially when four or five laws are missing from a larger theory
  (the largest recovery headroom);
* recovering coupled or decoupled explanations when two or three axioms are
  missing and only one law is observed;
* better candidate generation from the algebraic structure of the instance and
  better ranking, so that the first proposed set is the right one;
* avoiding unsound explanations (stronger-than-true or degenerate laws) without
  access to the complete theory;
* doing more within the fixed per-instance time limit on larger theories.

Out of scope: looking up or memorizing benchmark laws, reading evaluator files
(including their copies in the repository history or in job logs), proposing
contradictions or degenerate laws, copying or rearranging the observed laws and
known axioms, replacing exact derivability with numerical fits, or changing the
evaluator, instances, time limit or candidate budget.
