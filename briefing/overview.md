# Overview

The paper introduces AI-Noether, a system for repairing incomplete scientific
theories. Given polynomial background axioms and a target law that the
incomplete theory cannot derive, it proposes missing axioms whose addition
makes the target derivable, using algebraic geometry.

This gym measures that capability as exact symbolic abduction. Solvers receive
anonymized, unit-rescaled instances (known axioms, targets, which quantities are
measured or nonzero, and how many axioms are missing) and return a ranked list
of candidate axiom sets. The evaluator runs every solver itself under a fixed
time limit and checks each candidate exactly against the complete theory:
does it make the targets derivable, is it true in the complete theory, does it
add information, and does it recover the removed axioms.

* Train slice: the paper's twelve public benchmark theories (75 single-axiom
  removals as in the paper's Table 6, plus samples of two- and three-axiom
  removals as in Table 3).
* Test slice (held out): fourteen further physical theories that exist only on
  the evaluator side.

The reference solver implements the paper's exact Encode–Decompose–Reason
pipeline; the baselines are an empty answer and a syntax-guided enumerator.
The reference recovers every held-out single removal but often ranks a false
alternative first or proposes false laws next to the right one; two- and
three-axiom removals are where it falls short most, as in the paper.
