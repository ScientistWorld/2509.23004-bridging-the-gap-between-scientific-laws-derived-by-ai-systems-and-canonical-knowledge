# Overview

The paper introduces AI-Noether, a symbolic system for repairing incomplete scientific theories. Given polynomial background axioms and a target relation that the incomplete theory cannot derive, AI-Noether uses algebraic geometry to propose missing axioms whose addition makes the target derivable.

This workspace reproduces the exact symbolic core claim on single-missing-axiom benchmark cases from the simple harmonic oscillator and Kepler systems. It also defines broader exact single-axiom and Kepler multi-axiom scoring targets. The environment includes the official benchmark definitions, a runner for the paper's encode-decompose-reason algorithm, reusable evaluation scripts, and scoring targets for future agents.
