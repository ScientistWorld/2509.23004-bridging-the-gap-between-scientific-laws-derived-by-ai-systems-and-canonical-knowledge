# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-11 11:30] - none
- Read the paper and identified AI-Noether's exact encode-decompose-reason pipeline as the core method.
- Cloned the official AI-Noether benchmark repository into `method/`.
- Implemented the exact single-axiom runner, evaluator, scripts, reference scores, and documentation.
- Prepared a CPU test job to verify the method end-to-end before claiming `method_runs`.

### [2026-06-11 11:42] - core_claim
- Compute-node CPU smoke job completed successfully.
- Reproduced the core exact single-axiom claim on simple harmonic oscillator and Kepler: 11/11 canonical missing axioms recovered, with all 11 cases completed.
- Prepared a broader 75-case paper-counted single-axiom sweep for the next job.
