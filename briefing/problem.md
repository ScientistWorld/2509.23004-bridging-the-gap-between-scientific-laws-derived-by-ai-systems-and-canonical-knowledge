# Problem Definition

The task is **abductive inference for polynomial scientific theories**: given an
incomplete theory and an observed law it cannot explain, propose the missing
axioms.

Each instance is built from a complete theory: polynomial axioms
`A_1 = 0, ..., A_m = 0` over variables `x1..xn` together with one or more target
relations `Q = 0` that follow from the complete theory (`Q` is an algebraic
combination `Q = sum alpha_i A_i` with polynomial multipliers). Between one and
five axioms are removed. What remains is given to the solver:

| field | meaning |
|---|---|
| `variables` | ordered variable names `x1..xn` (anonymized physical quantities) |
| `measured_variables` | variables that occur in the observed targets |
| `nonzero_variables` | quantities that are physically nonzero in the complete theory (masses, lengths, ...) |
| `known_axioms` | the remaining axioms, as polynomial strings (each means `poly = 0`) |
| `targets` | the observed relation(s), not derivable from `known_axioms` alone (one law, or several in the multiple-consequence experiment) |
| `num_missing` | how many axioms were removed |
| `time_limit_seconds` | wall-clock budget for this instance |

The solver returns a **ranked list of candidate sets**; each set holds at most
`num_missing` polynomials (each again meaning `poly = 0`). Only the first five
sets are considered. A good answer:

1. makes every target derivable when added to the known axioms;
2. is true in the complete (hidden) theory wherever the declared nonzero
   quantities are nonzero, i.e. it does not contradict the theory, force a
   physical quantity to zero, or assert a law that is stronger than the theory;
3. adds information beyond what the known axioms and the target already state
   (the target itself, or the target divided by nonzero quantities, does not);
4. ideally recovers the removed axioms themselves (up to rescaling and
   substitution of known axioms), not only some sufficient relation.

No numerical data is provided for the missing axioms; inputs and outputs are exact
polynomials with rational coefficients. Polynomial strings use integers,
variable names, `+ - * ^` (or `**`), parentheses and division by integer
constants only.

## Slices

* **Train (visible):** the twelve published benchmark theories of the paper
  (classical mechanics, relativity, electromagnetism, semiconductor physics),
  in `data/systems_and_phenomena`, presented in the same anonymized and
  unit-rescaled form as the held-out slice, plus four larger extensions of
  them used only for multiple-consequence instances (`data/systems_mc_train`).
  Instances and their answers are in `eval/train/instances.json`.
* **Test (held out):** eighteen different physical theories (fourteen of
  comparable size, four larger ones for the multiple-consequence experiment)
  that are not published anywhere; only their evaluator-side copy exists. A method must
  therefore work from the algebraic structure of the instance, not from a memory
  of benchmark laws.

Each slice contains every well-posed single removal of each theory and a fixed
sample of two- and three-axiom removals. A removal is well posed when the
targets do not follow from the remaining axioms, not even wherever the nonzero
quantities are nonzero, and no removed axiom is already implied by the remaining
axioms and the targets. Multi-axiom removals are much harder:
often the targets do not determine each missing law separately, so a correct
answer may be a coupled relation that combines several missing laws.

The **multiple-consequence** instances remove two to five axioms and give
several observed laws: the theory's target plus laws that further experiments
would observe (each involves the measured quantities and one otherwise
unmeasured quantity). The observed laws are chosen so that, together with the
remaining axioms, they determine every removed axiom wherever the nonzero
quantities are nonzero. Here the goal is to recover the removed axioms
themselves, not a coupled substitute. Besides the theories of the other
experiments, this experiment uses larger theories (8-10 axioms, 12-16
variables; four held out, four in the train slice under
`data/systems_mc_train`).
