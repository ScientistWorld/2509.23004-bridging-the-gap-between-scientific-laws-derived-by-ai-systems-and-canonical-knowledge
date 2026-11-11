# Research Direction

This gym studies automated abductive inference for scientific laws written as
polynomial equations: recover the axioms missing from a theory, given the rest of
the theory and an observed law, with formal derivability.

Productive directions:

* recovering coupled or decoupled explanations when two or three axioms are
  missing (the largest headroom);
* better candidate generation from the algebraic structure of the instance and
  better ranking, so that the first proposed set is the right one;
* avoiding unsound explanations (stronger-than-true or degenerate laws) without
  access to the complete theory;
* doing more within the fixed per-instance time limit on larger theories.

Out of scope: looking up or memorizing benchmark laws, reading evaluator files,
proposing contradictions or degenerate laws, copying or rearranging the target
and known axioms, replacing exact derivability with numerical fits, or changing
the evaluator, instances, time limit or candidate budget.
