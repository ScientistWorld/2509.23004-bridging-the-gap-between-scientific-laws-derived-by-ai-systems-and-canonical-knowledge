# Constraints

The benchmark is about abductive recovery of polynomial axioms. Improvements must preserve the task and evaluation contract.

- Use the same benchmark systems and removed-axiom cases unless adding a clearly named new experiment.
- Write method outputs as JSON artifacts that `scripts/evaluate.sh` can score without importing method code.
- Do not hardcode paper results, reference answers, or evaluator outcomes into generated outputs.
- Do not change the evaluator to call the proposed method or regenerate candidates internally.
- Keep all symbolic problem assets in `data/` or `method/AI-Noether` and avoid references to local shared caches in committed code.
- Report all attempted cases, including timeouts or failures, so `cases_completed` remains meaningful.
- Any alternate method must still solve the same abductive problem: propose polynomial equations that make the target derivable from the incomplete theory.

Resource scaling is allowed for new experiments, but changing the problem into supervised prediction or numeric curve fitting is outside this gym's direction.
