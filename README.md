# Overview

The paper introduces AI-Noether, a symbolic system for repairing incomplete scientific theories. Given polynomial background axioms and a target relation that the incomplete theory cannot derive, AI-Noether uses algebraic geometry to propose missing axioms whose addition makes the target derivable.

This workspace reproduces the exact symbolic core claim on single-missing-axiom benchmark cases from the simple harmonic oscillator and Kepler systems. It also defines broader exact single-axiom and Kepler multi-axiom scoring targets. The environment includes the official benchmark definitions, a runner for the paper's encode-decompose-reason algorithm, reusable evaluation scripts, and scoring targets for future agents.

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

Each case is scored from saved candidate axiom sets. For single-missing-axiom cases, success requires recovering the removed canonical axiom while passing symbolic derivability checks for the target. For multi-missing-axiom cases, success follows the paper's coupled-recovery setting: a candidate may be entangled rather than a literal copy of every removed axiom, but it must be nondegenerate and make the target derivable. The main metric is `success_rate`, the fraction of benchmark cases solved. `derivable_candidate_rate` records whether each case produced any derivability-certified candidate, and `cases_completed` records how many cases ran to normal completion rather than timing out or failing.

The reproduced experiments are:

- `exact_single_axiom_core`: all 11 single-axiom cases from simple harmonic oscillator and Kepler.
- `exact_single_axiom_all_paper`: all 75 single-axiom cases reported in the paper's Appendix D.1 / Table 6.
- `simple_harmonic_single_axiom`: 6 single-axiom cases for the simple harmonic oscillator.
- `kepler_single_axiom`: 5 single-axiom cases for Kepler.
- `kepler_pair_axiom`: 10 two-missing-axiom cases for Kepler from Table 2.
- `kepler_triple_axiom`: 10 three-missing-axiom cases for Kepler from Table 2.

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

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: done
- **Working time**: 8m | **GPU**: 0.0h
- **Jobs**: 5 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-11 12:49] - core_claim_plus
- Validated the exact AI-Noether symbolic abduction environment with `python validate.py --compare`.
- Reproduced the core exact single-axiom claim on simple harmonic oscillator and Kepler: 11/11 recoveries.
- Expanded beyond the minimum to the paper-counted 75 exact single-axiom cases: 57/75 canonical recoveries and 62/75 derivable-candidate cases under the compact timeout.

### [2026-06-11 12:54] - core_claim_plus
- Audited the inherited workspace and confirmed the implementation follows the paper's exact encode, primary-decompose, and reason algorithm.
- Strengthened the evaluator so new outputs are symbolically rescored outside `method/`.
- Prepared a CPU job for the Kepler pair/triple missing-axiom experiments from Table 2.

### [2026-06-11 13:01] - core_claim_plus
- Reviewed completed Kepler multi-axiom job `9543f132-504`.
- Fixed target-tautology candidate selection by filtering generators already implied by remaining axioms plus targets.
- Updated multi-axiom evaluation semantics to count strong coupled derivability rather than canonical recovery of every removed axiom.

### [2026-06-11 13:02] - core_claim_plus
- Reviewed completed Kepler multi-axiom rerun `71a51b0b-a58`.
- The rerun completed all 20 Kepler pair/triple cases and `python validate.py --compare` passed.
- Secondary Kepler Table 2 reproduction remains partial: 1/10 pair cases and 0/10 triple cases under the non-tautological strong-derivability criterion, so the milestone stays at `core_claim_plus`.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: error
- **Working time**: 41m | **GPU**: 0.0h
- **Jobs**: 9 total (7 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-11 13:15] - core_claim
- Audited the inherited exact AI-Noether implementation and confirmed it implements the paper's encode, primary-decompose, and symbolic-reason workflow rather than a surrogate.
- Confirmed the existing single-axiom core reproduction remains valid: simple harmonic oscillator 6/6, Kepler 5/5, and combined core 11/11 in `scoring/scores.json`.
- Found that Kepler pair/triple documentation and scoring were inconsistent with the paper's coupled-recovery criterion; patched the evaluator and prepared a CPU rerun to regenerate the secondary scores.

### [2026-06-11 13:22] - core_claim
- Reviewed job `04eec4cc-06f`: all single-axiom core and all-paper results still validate, but pre-decomposition Kepler nondegenerate saturation erased all pair/triple candidate sets.
- Split Kepler nondegeneracy handling into post-decomposition candidate filtering so multi-axiom cases can still expose coupled explanations while rejecting zero-factor branches.
- Fixed the no-abduction baseline to use the same 75 paper-counted single-axiom cases as the method run.

### [2026-06-11 13:29] - core_claim_plus
- Reviewed job `7227dc15-43e`: corrected Kepler pair/triple filtering completed all 20 cases and restored nonzero multi-axiom recovery.
- Reproduced Kepler pair recovery at 5/10 coupled successes and 7/10 derivability-certified cases; reproduced Kepler triple recovery at 1/10 coupled successes and 4/10 derivability-certified cases.
- Confirmed the no-abduction baseline now appears in the 75-case all-paper score with 75/75 completed and zero recoveries, preserving the evaluation constraint.
- Added rational-denominator clearing for benchmark equations so two known rational-coefficient validation errors can be rerun without changing the underlying ideal.

### [2026-06-11 13:53] - core_claim_plus
- Cancelled job `7970b925-534` after it exposed new integer-domain failures on rational candidate generators emitted by Singular.
- Patched the method and evaluator to run SymPy Groebner and polynomial comparisons over `QQ`, and normalized decomposed candidate generators before symbolic checks.
- Prepared a targeted rational-coefficient smoke job before attempting another full all-paper rerun.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim_plus` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h
- **Jobs**: 9 total (7 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-11 13:15] - core_claim
- Audited the inherited exact AI-Noether implementation and confirmed it implements the paper's encode, primary-decompose, and symbolic-reason workflow rather than a surrogate.
- Confirmed the existing single-axiom core reproduction remains valid: simple harmonic oscillator 6/6, Kepler 5/5, and combined core 11/11 in `scoring/scores.json`.
- Found that Kepler pair/triple documentation and scoring were inconsistent with the paper's coupled-recovery criterion; patched the evaluator and prepared a CPU rerun to regenerate the secondary scores.

### [2026-06-11 13:22] - core_claim
- Reviewed job `04eec4cc-06f`: all single-axiom core and all-paper results still validate, but pre-decomposition Kepler nondegenerate saturation erased all pair/triple candidate sets.
- Split Kepler nondegeneracy handling into post-decomposition candidate filtering so multi-axiom cases can still expose coupled explanations while rejecting zero-factor branches.
- Fixed the no-abduction baseline to use the same 75 paper-counted single-axiom cases as the method run.

### [2026-06-11 13:29] - core_claim_plus
- Reviewed job `7227dc15-43e`: corrected Kepler pair/triple filtering completed all 20 cases and restored nonzero multi-axiom recovery.
- Reproduced Kepler pair recovery at 5/10 coupled successes and 7/10 derivability-certified cases; reproduced Kepler triple recovery at 1/10 coupled successes and 4/10 derivability-certified cases.
- Confirmed the no-abduction baseline now appears in the 75-case all-paper score with 75/75 completed and zero recoveries, preserving the evaluation constraint.
- Added rational-denominator clearing for benchmark equations so two known rational-coefficient validation errors can be rerun without changing the underlying ideal.

### [2026-06-11 13:53] - core_claim_plus
- Cancelled job `7970b925-534` after it exposed new integer-domain failures on rational candidate generators emitted by Singular.
- Patched the method and evaluator to run SymPy Groebner and polynomial comparisons over `QQ`, and normalized decomposed candidate generators before symbolic checks.
- Prepared a targeted rational-coefficient smoke job before attempting another full all-paper rerun.

</details>


---

# Reproduction Milestones

**Current: core_claim_plus**

## Stop Justification
- Completed at milestone `core_claim_plus`.
