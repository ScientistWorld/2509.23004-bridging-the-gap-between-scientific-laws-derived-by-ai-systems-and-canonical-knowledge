# Method

AI-Noether performs abductive inference for polynomial scientific theories using an encode, decompose, and reason pipeline.

First, the incomplete background axioms and the target hypothesis are encoded as a polynomial ideal. Second, the corresponding variety is decomposed into irreducible components using primary decomposition. Third, generators from those components are treated as candidate missing axioms and verified by algebraic reasoning: if adding a candidate to the incomplete axiom set makes the target polynomial reduce to zero under Groebner-basis reasoning, the candidate is accepted.

This reproduction targets the exact symbolic branch of the paper. It uses the official AI-Noether benchmark systems and wraps the exact algorithm with a compact runner that:

- removes each single axiom from a benchmark system,
- encodes the remaining axioms plus the target,
- calls Singular for primary decomposition,
- enumerates component generators as one-axiom candidates,
- verifies target derivability with symbolic Groebner reduction, and
- records whether the recovered candidate also matches the removed canonical axiom.

The noisy witness-set and theorem-prover branch is not part of the initial core reproduction. The code is organized so those experiments can be added later without changing the evaluator interface.
