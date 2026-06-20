# Progress

## What Works

The workspace now contains a runnable exact symbolic reproduction path for AI-Noether's single-missing-axiom benchmark setting. The implementation wraps the official benchmark systems and executes the paper's encode, primary-decompose, and reason workflow across the paper-counted single-axiom systems.

The evaluator is independent from `method/` and scores saved method outputs only. For newly generated outputs, it recomputes derivability and canonical recovery from the saved symbolic candidates rather than trusting method-provided success flags. A no-abduction baseline is available for evaluator sanity checks.

Continuation audit on 2026-06-20 found that the current checked-in `scoring/scores.json` is stale and only contains the no-abduction baseline. This does not invalidate the method implementation, but it means the visible score artifact must be regenerated before restoring a milestone above `core_claim`. The prepared job now runs `scripts/reproduce.sh` and `validate.py --compare` to rebuild baseline, method, multi-axiom, and score artifacts together.

## Results Achieved

The CPU smoke job completed successfully on the compute node and wrote `scoring/scores.json`.

Reference paper targets recorded in `scoring/reference.json`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 73/75.
- Kepler pair missing axioms: 7/10.
- Kepler triple missing axioms: 2/10.

Reproduced results after job `7227dc15-43e`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 57/75 canonical recoveries, 62/75 cases with at least one derivable candidate, and 62/75 cases completed without error or timeout.
- No-abduction baseline: 0/75 all-paper recoveries with all 75 cases completed; 0/11 core recoveries with all 11 core cases completed.
- Kepler pair missing axioms: 5/10 coupled-success cases and 7/10 derivability-certified cases after post-decomposition degeneracy filtering.
- Kepler triple missing axioms: 1/10 coupled-success cases and 4/10 derivability-certified cases after post-decomposition degeneracy filtering.

## What Remains

- Rerun the full exact single-axiom sweep after rational-denominator normalization and regenerate `scoring/scores.json` from the fresh method outputs.
- Improve the all-paper score by optimizing the exact symbolic reasoning step for the remaining Compton and relativistic cases that time out under the CPU job limit.
- Investigate the remaining non-timeout misses in inelastic collision and photo-Hall systems; the evaluator records candidates but the strict canonical-recovery check does not certify the removed axiom.
- Improve the Kepler multi-axiom reproduction by matching the paper's full projection filtering and coupled-relation selection procedure more closely; the present implementation is honest but stricter than the reported Table 2 criterion.
- Add additional pair/triple missing-axiom systems beyond Kepler if future compute budget allows.

## Issues Encountered

The official repository contains broader noisy and theorem-prover workflows, but the initial reproduction focuses on the exact symbolic branch because it directly supports the paper's main data-free abductive inference claim and can run without external datasets.

A first broad all-paper sweep attempt was canceled after the Compton first-axiom case produced no method-level progress output and no final JSON. The runner now logs every case, writes `scoring/ai_noether_exact_outputs.json` incrementally after each completed case, and enforces a whole-case timeout in addition to the Singular decomposition timeout. The retry also schedules Compton last so other paper systems can finish first.

The completed 75-case retry used a 120-second whole-case timeout to fit the scheduler's one-hour CPU job limit. Most systems complete quickly, but 9 Compton cases and 2 relativistic-law cases time out in the reasoning stage after decomposition. Two additional cases hit SymPy rational-coefficient handling errors. These are implementation limits of the compact reproduction, not changes to the paper's algorithm.

The continuation audit found the method implementation to be a real exact AI-Noether encode/decompose/reason pipeline rather than a surrogate. It also found that the previous evaluator trusted success flags from method outputs. The evaluator now independently recomputes symbolic validity for new outputs that include variables, remaining axioms, targets, and accepted candidate polynomials.

Job `9543f132-504` completed all 20 Kepler pair/triple cases in about one minute, but produced 0 canonical recoveries for both pair and triple settings. Inspection showed this was not a method crash; multi-axiom cases often recover coupled relations rather than individual canonical axioms. The job also revealed target-tautology candidates in the accepted sets, which have now been filtered.

Job `71a51b0b-a58` reran all 20 Kepler pair/triple cases after the non-tautology filter and completed successfully. The evaluator merged the new multi-axiom output with the existing single-axiom sweep and validated the score file. The resulting secondary scores are below the paper's Table 2: 1/10 Kepler pair cases and 0/10 Kepler triple cases under the current strong coupled-derivability scoring.

Job `04eec4cc-06f` completed with exit code 0 and validated the combined score file, but the Kepler pair/triple sweep used ideal saturation by the nonzero physical factors before primary decomposition. That removed all 20 Kepler multi-axiom candidate sets. This is not a method crash, but it is too restrictive compared with the intended nondegenerate-branch filtering. The runner now separates algebraic saturation from post-decomposition filtering, and the checked-in scripts use the latter for Kepler multi-axiom reruns.

The no-abduction baseline initially enumerated all 77 parsed single-axiom removals, including two Hall axioms outside the paper-counted 75-case table used by the method run. The baseline script now applies the same `hall=7` cap as the method run so all-paper baseline and method scores are comparable.

Job `7227dc15-43e` completed successfully and confirmed the corrected Kepler multi-axiom setup. The pair setting now reaches the paper's 7/10 count on derivability-certified candidates and 5/10 on the stricter coupled-success metric. The triple setting reaches 4/10 on derivability-certified candidates and 1/10 on coupled success. This supports `core_claim_plus` but remains a partial reproduction of the paper's secondary multi-axiom result.

Two all-paper single-axiom failures are rational-coefficient representation errors (`1/2` in escape velocity and `4/5` in inelastic relativistic collision). The method runner now clears rational denominators when loading benchmark equations and targets; multiplying a polynomial generator by a nonzero rational scalar preserves the ideal over characteristic zero.

Job `7970b925-534` was cancelled during the full rerun because the rational-denominator patch fixed the original escape-velocity case but exposed the same integer-domain error on rational candidate generators emitted by Singular. The runner now normalizes candidate generators before checking them, and both the method and evaluator use SymPy Groebner bases over `QQ` instead of the default integer domain. The next submitted job is a targeted smoke test over the affected systems and writes separate `scoring/rational_smoke_*` artifacts rather than overwriting the main scores.

## Deviations from Paper

The first completed job scaled the experiment to two exact single-axiom benchmark systems rather than all reported systems. The later completed job expands to the paper-counted 75 single-axiom cases, using the same algorithmic procedure: polynomial encoding, primary decomposition, candidate extraction, and symbolic derivability verification. The compact reproduction imposes a per-case timeout so the reusable environment finishes reliably under the available CPU wall-time limit.

The Kepler pair/triple exact missing-axiom setting from Table 2 is run with the same encode, decompose, enumerate, and verify procedure, scaling only the number of removed axioms and candidate-set size. The compact reproduction uses Singular plus SymPy rather than the paper's Macaulay2 verifier, but it preserves the same algebraic membership check and now records coupled explanations separately from literal canonical recovery.
