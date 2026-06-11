# Reproduction Milestones

**Current: core_claim_plus**

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

### [2026-06-11 12:20] - core_claim
- Canceled the first broad 75-case sweep because it stalled silently in the initial Compton case and did not produce a completed score file.
- Added per-case progress logs, incremental output writes, and a whole-case timeout so expensive cases cannot block all results.
- Prepared a retry that runs Compton last while keeping the same exact encode-decompose-reason method.

### [2026-06-11 12:46] - core_claim_plus
- Completed the paper-counted 75-case exact single-axiom sweep on the compute node.
- Reproduced the core subset at 11/11 and extended the run across all reported single-axiom systems.
- Overall all-paper compact result: 57/75 canonical recoveries, 62/75 derivable-candidate recoveries, and 62/75 cases completed before timeout or error.
