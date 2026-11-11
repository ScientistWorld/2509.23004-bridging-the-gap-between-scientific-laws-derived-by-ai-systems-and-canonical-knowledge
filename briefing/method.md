# Method (reference implementation)

AI-Noether performs abductive inference for polynomial theories with an
Encode–Decompose–Reason pipeline (paper Section 2.1, Algorithm 1 in
Appendix E.3). The reference solver is `scripts/solvers/ai_noether_exact.sh`,
which runs `method/exact_abduction_runner.py` on one instance:

1. **Encode** the known axioms and the targets as one ideal
   `I = <A_1..A_k, Q_1..Q_s>`.
2. **Decompose** its variety into irreducible components: Singular `minAss`
   (minimal associated primes), as in the paper's implementation. The generators
   of each prime component are candidate axioms; generators already in
   `<known axioms, targets>` carry no new information and are dropped (as in the
   official code's `generate_candidate_sets`).
3. **Reason**: every subset of one component's generators with at most
   `num_missing` elements is added to the known axioms. A set is accepted when
   each target lies in the elimination ideal onto the target's measured
   variables (weak test, ideal membership) and the augmented theory does not
   force a declared nonzero quantity (or 1) to zero (degeneracy filtering,
   Appendix E.2). The strong test checks that the target appears literally (up
   to a scalar) in the reduced lexicographic Groebner basis of that projection.
4. **Rank** as in Appendix E.2's two tiers: inclusion-minimal strong sets first,
   then the remaining minimal weak sets; ties broken by parsimony (fewer
   polynomials, fewer terms, lower degree).

All Groebner basis work runs in Singular (the paper uses Macaulay2 for this
step and Singular for decomposition). The decomposition gets at most 70% of the
per-instance budget; reasoning stops before the deadline and returns what it
has accepted.

Switches used in the hardening audit (not the reference setting):
`--saturate` (remove degenerate components before decomposing),
`--extra-orders` (also take generators from Groebner bases of each component
in two other monomial orders), `--saturation-only` (one saturated component
instead of a primary decomposition), `--canonical` (reduced Groebner basis of
each prime as its generators), `--dim-rank` (top-dimensional components first),
`--sign-prior` (sign-based filtering and ranking of candidates),
`--drop-restatements`, `--no-rank`, `--max-set-size`, `--no-degenerate-filter`,
`--no-reason`; `AINOETHER_NO_ASLR=1` runs Singular with a fixed memory layout.

Singular's `minAss` returns different (equally valid) generating sets of the
same prime components from run to run, also with a fixed `--random` seed and a
fixed memory layout, as in the official code. The reference's outputs therefore
vary on about 15% of instances; its weighted score moves by about +-0.005.

The paper's noisy pathway (numerical irreducible decomposition with witness
sets, symbolic regression, KeYmaera X existential reasoning) is not
reproduced; this gym measures the exact symbolic setting.
