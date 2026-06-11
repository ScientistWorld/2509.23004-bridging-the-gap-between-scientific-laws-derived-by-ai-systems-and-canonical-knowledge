# Progress

## What Works

The workspace now contains a runnable exact symbolic reproduction path for AI-Noether's single-missing-axiom benchmark setting. The implementation wraps the official benchmark systems and executes the paper's encode, primary-decompose, and reason workflow for the simple harmonic oscillator and Kepler systems.

The evaluator is independent from `method/` and scores saved method outputs only. A no-abduction baseline is available for evaluator sanity checks.

## Results Achieved

The CPU smoke job completed successfully on the compute node and wrote `scoring/scores.json`.

Reference paper targets recorded in `scoring/reference.json`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.

Reproduced core results:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.

## What Remains

- Run the 75-case all-paper exact single-axiom sweep across the checked-in official benchmark tree.
- If time remains, add pair/triple missing-axiom cases.

## Issues Encountered

The official repository contains broader noisy and theorem-prover workflows, but the initial reproduction focuses on the exact symbolic branch because it directly supports the paper's main data-free abductive inference claim and can run without external datasets.

## Deviations from Paper

The first completed job scaled the experiment to two exact single-axiom benchmark systems rather than all reported systems. The next job expands to the paper-counted 75 single-axiom cases, using the same algorithmic procedure: polynomial encoding, primary decomposition, candidate extraction, and symbolic derivability verification.
