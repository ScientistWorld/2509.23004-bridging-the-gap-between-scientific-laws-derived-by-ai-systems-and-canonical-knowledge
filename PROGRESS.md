# Progress

## What Works

The workspace now contains a runnable exact symbolic reproduction path for AI-Noether's single-missing-axiom benchmark setting. The implementation wraps the official benchmark systems and executes the paper's encode, primary-decompose, and reason workflow for the simple harmonic oscillator and Kepler systems.

The evaluator is independent from `method/` and scores saved method outputs only. A no-abduction baseline is available for evaluator sanity checks.

## Results Achieved

No compute-node results have been recorded yet in this iteration. The next submitted job will run the core exact single-axiom reproduction and write `scoring/scores.json`.

Reference paper targets recorded in `scoring/reference.json`:

- Simple harmonic oscillator single missing axiom: 6/6.
- Kepler single missing axiom: 5/5.
- Combined core subset: 11/11.

## What Remains

- Run the CPU smoke job in the target container.
- Inspect `scoring/scores.json` and compare against `reference.json`.
- If the exact core succeeds, update the milestone to `core_claim`.
- If time remains, add additional systems or pair/triple missing-axiom cases.

## Issues Encountered

The official repository contains broader noisy and theorem-prover workflows, but the initial reproduction focuses on the exact symbolic branch because it directly supports the paper's main data-free abductive inference claim and can run without external datasets.

## Deviations from Paper

This first job scales the experiment to two exact single-axiom benchmark systems rather than all reported systems. The algorithmic procedure is preserved: polynomial encoding, primary decomposition, candidate extraction, and symbolic derivability verification.
