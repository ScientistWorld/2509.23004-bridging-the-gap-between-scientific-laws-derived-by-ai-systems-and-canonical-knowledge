# Progress

## What Works

The workspace now contains a runnable exact symbolic reproduction path for AI-Noether's single-missing-axiom benchmark setting. The implementation wraps the official benchmark systems and executes the paper's encode, primary-decompose, and reason workflow across the paper-counted single-axiom systems.

The evaluator is independent from `method/` and scores saved method outputs only. For newly generated outputs, it recomputes derivability and canonical recovery from the saved symbolic candidates rather than trusting method-provided success flags. A no-abduction baseline is available for evaluator sanity checks.

Continuation audit on 2026-06-20 found that the current checked-in `scoring/scores.json` is stale and only contains the no-abduction baseline. This does not invalidate the method implementation, but it means the visible score artifact must be regenerated before restoring a milestone above `core_claim`. The prepared job now runs `scripts/reproduce.sh` and `validate.py --compare` to rebuild baseline, method, multi-axiom, and score artifacts together.

A follow-up check at 2026-06-20 07:47 found no fresh full-run artifacts yet. The existing rational smoke output has no `"expected an integer"` failures, so the next step remains the full exact method rerun rather than another rational-only smoke test.

At 2026-06-20 07:50, `validate.py --compare` still reported only no-abduction baseline reproduction entries in `scoring/scores.json`. The full CPU reproduction remained the required next step; no method or evaluator code changes were made during that check.

At 2026-06-20 07:53, `scoring/scores.json` was regenerated from the saved method artifacts. This restored proposed-method score entries for every target experiment, but the exact single-axiom core score is only 9/11 because the saved exact output predates the rational-coefficient fix for two simple harmonic oscillator cases. The next submitted job is narrowed to rerun the current code on the core systems and Kepler pair/triple cases so the milestone can be restored from fresh outputs.

At 2026-06-20 07:56, the saved rational-coefficient smoke artifact was merged with the prior exact sweep. This uses real compute-node outputs only: the current-code rational smoke contributes the six simple harmonic oscillator cases, and the prior exact sweep contributes the five Kepler single-axiom cases and broader non-duplicate systems. The merged artifact restores 11/11 exact single-axiom core recovery and keeps the Kepler pair/triple secondary scores visible.

Continuation audit at 2026-06-20 08:04 found the reproduction intact. The method code still matches the paper's symbolic AI-Noether pipeline, the evaluator remains independent from `method/`, and standalone `scripts/evaluate.sh` followed by `python validate.py --compare` reproduces the checked-in scores without changes.

Continuation audit at 2026-06-20 08:12 found two scoring integrity gaps that needed correction before keeping the higher milestone. The evaluator had a compatibility path that trusted success flags for incomplete non-empty artifacts, and the Kepler multi-axiom degeneracy constraint was documented but not represented as an explicit score metric. The evaluator now rejects incomplete non-empty artifacts, recomputes degenerate-boundary candidates by ideal membership, and reports `nondegenerate_candidate_rate`. Benchmark system files have also been mirrored into `data/systems_and_phenomena` so baseline and method entry points consume data assets from `data/` rather than method-private paths.

CPU validation job `809a51f1-bf9` regenerated scores with the stricter evaluator. Its first validation pass failed because `degenerate_candidate_count` was present in result objects but missing from the reference metric schema. After declaring that constraint metric, `python validate.py --compare` passes. The restored core result remains 11/11 for AI-Noether exact recovery against 0/11 for the no-abduction baseline, with `nondegenerate_candidate_rate=1.0` across the scored experiments.

## Results Achieved

The CPU smoke job completed successfully on the compute node and wrote `scoring/scores.json`.

Reference paper targets recorded in `scoring/reference.json`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 73/75.
- Kepler pair missing axioms: 7/10.
- Kepler triple missing axioms: 2/10.

Reproduced results currently in `scoring/scores.json` after merging saved compute artifacts:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 52 canonical recoveries and 56 derivability-certified recoveries over the 65 cases available in saved method outputs; the 10 Compton cases remain absent from the merged artifact.
- No-abduction baseline: 0/75 all-paper recoveries with all 75 cases completed; 0/11 core recoveries with all 11 core cases completed.
- Kepler pair missing axioms: 5/10 coupled-success cases and 7/10 derivability-certified cases after post-decomposition degeneracy filtering.
- Kepler triple missing axioms: 1/10 coupled-success cases and 4/10 derivability-certified cases after post-decomposition degeneracy filtering.

## What Remains

- Rerun the full exact single-axiom sweep after rational-denominator normalization and regenerate `scoring/scores.json` from the fresh method outputs.
- Run a fresh full 75-case exact sweep with the rational-denominator fix if pursuing a milestone beyond `core_claim_plus`.
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

The 2026-06-20 continuation audit found an evaluator fallback that could trust incomplete non-empty artifacts. That path has been removed for proposed-method outputs; zero-candidate artifacts can still score as failures without SymPy, but any artifact claiming candidates or success must include the symbolic fields needed for independent recomputation.

## Deviations from Paper

The first completed job scaled the experiment to two exact single-axiom benchmark systems rather than all reported systems. The later completed job expands to the paper-counted 75 single-axiom cases, using the same algorithmic procedure: polynomial encoding, primary decomposition, candidate extraction, and symbolic derivability verification. The compact reproduction imposes a per-case timeout so the reusable environment finishes reliably under the available CPU wall-time limit.

The Kepler pair/triple exact missing-axiom setting from Table 2 is run with the same encode, decompose, enumerate, and verify procedure, scaling only the number of removed axioms and candidate-set size. The compact reproduction uses Singular plus SymPy rather than the paper's Macaulay2 verifier, but it preserves the same algebraic membership check and now records coupled explanations separately from literal canonical recovery.
