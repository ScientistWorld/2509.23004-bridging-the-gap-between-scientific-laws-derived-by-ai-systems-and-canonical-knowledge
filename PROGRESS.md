# Progress

## What Works

The workspace now contains a runnable exact symbolic reproduction path for AI-Noether's single-missing-axiom benchmark setting. The implementation wraps the official benchmark systems and executes the paper's encode, primary-decompose, and reason workflow across the paper-counted single-axiom systems.

The evaluator is independent from `method/` and scores saved method outputs only. For newly generated outputs, it recomputes derivability and canonical recovery from the saved symbolic candidates rather than trusting method-provided success flags. A no-abduction baseline is available for evaluator sanity checks.

## Results Achieved

The CPU smoke job completed successfully on the compute node and wrote `scoring/scores.json`.

Reference paper targets recorded in `scoring/reference.json`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 73/75.
- Kepler pair missing axioms: 7/10.
- Kepler triple missing axioms: 2/10.

Reproduced core results:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.
- All paper-counted exact single missing axiom cases: 57/75 canonical recoveries, 62/75 cases with at least one derivable candidate, and 62/75 cases completed without error or timeout.

## What Remains

- A CPU job is queued to run Kepler pair/triple missing-axiom cases and merge the result with the existing single-axiom score file.
- Improve the all-paper score by optimizing the exact symbolic reasoning step for the remaining Compton and relativistic cases that time out under the one-hour CPU job limit.
- Investigate the remaining non-timeout misses in inelastic collision and photo-Hall systems; the evaluator records candidates but the strict canonical-recovery check does not certify the removed axiom.
- Add additional pair/triple missing-axiom systems beyond Kepler if future compute budget allows.

## Issues Encountered

The official repository contains broader noisy and theorem-prover workflows, but the initial reproduction focuses on the exact symbolic branch because it directly supports the paper's main data-free abductive inference claim and can run without external datasets.

A first broad all-paper sweep attempt was canceled after the Compton first-axiom case produced no method-level progress output and no final JSON. The runner now logs every case, writes `scoring/ai_noether_exact_outputs.json` incrementally after each completed case, and enforces a whole-case timeout in addition to the Singular decomposition timeout. The retry also schedules Compton last so other paper systems can finish first.

The completed 75-case retry used a 120-second whole-case timeout to fit the scheduler's one-hour CPU job limit. Most systems complete quickly, but 9 Compton cases and 2 relativistic-law cases time out in the reasoning stage after decomposition. Two additional cases hit SymPy rational-coefficient handling errors. These are implementation limits of the compact reproduction, not changes to the paper's algorithm.

The continuation audit found the method implementation to be a real exact AI-Noether encode/decompose/reason pipeline rather than a surrogate. It also found that the previous evaluator trusted success flags from method outputs. The evaluator now independently recomputes symbolic validity for new outputs that include variables, remaining axioms, targets, and accepted candidate polynomials.

## Deviations from Paper

The first completed job scaled the experiment to two exact single-axiom benchmark systems rather than all reported systems. The later completed job expands to the paper-counted 75 single-axiom cases, using the same algorithmic procedure: polynomial encoding, primary decomposition, candidate extraction, and symbolic derivability verification. The compact reproduction imposes a per-case timeout so the reusable environment finishes reliably under the available CPU wall-time limit.

The next job adds the Kepler pair/triple exact missing-axiom setting from Table 2. It preserves the same procedure and scales only the number of removed axioms and candidate-set size.
