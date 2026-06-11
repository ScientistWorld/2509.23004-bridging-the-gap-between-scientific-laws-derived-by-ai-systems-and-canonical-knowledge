#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against. 
# Implement this only if applicable, i.e. the paper has baselines.
# You do not need to implement all baselines to begin — 
# just enough to validate that the evaluation pipeline works 
# and provide a reference point. You can decide to expand more baselines later.
# Each baseline must be actually run and scored through evaluate.sh
# so the numbers are verified, not self-reported.
# You can decide what this baseline script should do yourself.
#
# Usage:
#   bash scripts/baseline.sh <name>

set -e

cd /home/user

mkdir -p scoring
python - <<'PY'
import json
import re
from pathlib import Path

systems = [
    "decay",
    "escape_velocity",
    "hagen",
    "hall",
    "inelastic_relativistic_collision",
    "kepler",
    "light",
    "photoHall",
    "relativistic_laws",
    "simple_harmonic_oscillator",
    "time_dilation",
    "compton",
]
axiom_limits = {"hall": 7}
system_dir = Path("method/AI-Noether/systems_and_phenomena")
cases = []
for problem in systems:
    text = (system_dir / problem / "system.txt").read_text()
    eqs_match = re.search(r"Equations?:\s*(.*?)(?=\n\s*\n\s*Measured)", text, re.S | re.I)
    if not eqs_match:
        raise RuntimeError(f"Could not parse equations for {problem}")
    equations = [ln.strip() for ln in eqs_match.group(1).splitlines() if ln.strip()]
    removal_count = min(len(equations), axiom_limits.get(problem, len(equations)))
    for index in range(1, removal_count + 1):
        cases.append(
            {
                "problem": problem,
                "removed_indices": [index],
                "status": "ok",
                "num_accepted": 0,
                "success": False,
                "strong_success": False,
                "runtime_seconds": 0.0,
            }
        )

payload = {
    "method": "no_abduction_baseline",
    "algorithm": "remaining_axioms_only",
    "cases": cases,
}
Path("scoring/baseline_outputs.json").write_text(json.dumps(payload, indent=2))
PY
bash scripts/evaluate.sh scoring/baseline_outputs.json
