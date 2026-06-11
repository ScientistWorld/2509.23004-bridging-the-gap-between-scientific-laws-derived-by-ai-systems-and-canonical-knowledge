# Overview

The paper introduces AI-Noether, a symbolic system for repairing incomplete scientific theories. Given polynomial background axioms and a target relation that the incomplete theory cannot derive, AI-Noether uses algebraic geometry to propose missing axioms whose addition makes the target derivable.

This workspace reproduces the exact symbolic core claim on single-missing-axiom benchmark cases from the simple harmonic oscillator and Kepler systems. The environment includes the official benchmark definitions, a runner for the paper's encode-decompose-reason algorithm, reusable evaluation scripts, and scoring targets for future agents.

---

# Problem Definition

The benchmark is polynomial abductive inference for scientific theories. Each instance provides:

- a finite set of background polynomial equations treated as known axioms,
- one or more polynomial target hypotheses, and
- a deliberately incomplete axiom set produced by removing one or more required axioms.

The task is to propose additional polynomial equations which, when added to the incomplete axiom set, make the target hypothesis algebraically derivable. A candidate succeeds only if it is not merely numerically correlated with the target but actually closes the logical gap between the incomplete theory and the target relation.

The core setting reproduced here is exact symbolic recovery with one missing axiom on two benchmark physical systems:

- simple harmonic oscillator, with 6 single-axiom removal cases;
- Kepler/orbital dynamics, with 5 single-axiom removal cases.

Inputs and outputs are symbolic polynomial strings, not sampled data. Evaluation must be independent of any particular implementation: a future method may use a different search strategy as long as it writes the same output format for recovered candidates.

---

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

---

# Evaluation Protocol

Evaluation reads method artifacts from `scoring/ai_noether_exact_outputs.json` or a compatible JSON file. It does not import from `method/` and does not rerun candidate generation.

Each case is scored by whether the method produced at least one candidate axiom set that recovers the removed canonical axiom while passing symbolic derivability checks for the target. The main metric is `success_rate`, the fraction of benchmark cases solved. `derivable_candidate_rate` records whether each case produced any derivability-certified candidate, and `cases_completed` records how many cases ran to normal completion rather than timing out or failing.

The reproduced experiments are:

- `exact_single_axiom_core`: all 11 single-axiom cases from simple harmonic oscillator and Kepler.
- `exact_single_axiom_all_paper`: all 75 single-axiom cases reported in the paper's Appendix D.1 / Table 6.
- `simple_harmonic_single_axiom`: 6 single-axiom cases for the simple harmonic oscillator.
- `kepler_single_axiom`: 5 single-axiom cases for Kepler.

The paper reports 6/6 and 5/5 success for these two single-axiom systems, so the core reference target is 11/11. A no-abduction baseline that returns no candidates scores 0/11 and is included to validate that the evaluator is measuring recovered explanations rather than simply counting completed cases.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 19m | **GPU**: 0.0h
- **Jobs**: 3 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

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

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
