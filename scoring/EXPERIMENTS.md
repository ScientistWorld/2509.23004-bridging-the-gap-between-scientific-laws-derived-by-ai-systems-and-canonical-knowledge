# Experiments

All experiments use the same interface and checks (see `briefing/evaluation.md`).
Each instance removes axioms from a complete polynomial theory; a solver sees the
remaining axioms, the target law(s), which variables are measured or nonzero, and
how many axioms are missing. Only the first five ranked candidate sets count.

## single_missing_axiom (weight 0.40)

Establishes whether a method can reconstruct one missing law of a theory from
the rest of the theory and an observed consequence, without data for the missing
law. Every single removal whose target is no longer derivable is included. The
primary metric is exact recovery (the proposed law, together with the known
axioms, implies the removed axiom on the physical locus); the paper reports
near-complete success on its benchmark, so this experiment mainly checks that a
method keeps this capability, ranks the right law first and does not propose
false laws alongside it.

## two_missing_axioms (weight 0.35)

Establishes whether a method can still explain an observed law when two laws are
missing. The targets often do not pin down each missing law separately, so the
primary metric credits any valid explanation: a set of at most two polynomials
that makes the targets derivable, is true in the complete theory, and adds
information beyond the targets. Exact recovery of both laws separately is
reported as a diagnostic only: with a single observed target it is out of reach
for every method tried so far. The paper reports roughly half of such cases
solved; this is where better methods can show headroom.

## three_missing_axioms (weight 0.25)

The same question with three missing laws (at most three proposed polynomials).
The paper reports roughly a quarter of such cases solved; most of the remaining
headroom of the gym is here.

## Constraint in every experiment

`unsound_rate` counts instances where some considered candidate set makes the
targets derivable only by being false in the complete theory (wherever the
physical quantities that are nonzero in it are nonzero) — a contradiction, a law
that forces a physical quantity to zero, or a law stronger than the theory —
plus every instance whose run failed. It protects against "explaining" anything
by asserting too much; true laws in an unfamiliar form are not penalized.

## Baselines (method rows, not experiments)

`no_abduction_baseline` keeps the incomplete theory (scores zero on every
benefit metric). `enumerative_baseline` tries small binomial laws by brute force
for a few seconds per instance.
