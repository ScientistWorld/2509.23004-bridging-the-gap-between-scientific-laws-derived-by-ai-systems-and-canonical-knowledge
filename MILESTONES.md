# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-11 13:15] - core_claim
- Audited the inherited exact AI-Noether implementation and confirmed it implements the paper's encode, primary-decompose, and symbolic-reason workflow rather than a surrogate.
- Confirmed the existing single-axiom core reproduction remains valid: simple harmonic oscillator 6/6, Kepler 5/5, and combined core 11/11 in `scoring/scores.json`.
- Found that Kepler pair/triple documentation and scoring were inconsistent with the paper's coupled-recovery criterion; patched the evaluator and prepared a CPU rerun to regenerate the secondary scores.

## Stop Justification
- Active reproduction has reached `core_claim`; the next submitted CPU job tests whether the corrected Kepler multi-axiom scoring supports a higher milestone.
