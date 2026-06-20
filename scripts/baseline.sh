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
system_dir = Path("data/systems_and_phenomena")
cases = []
for problem in systems:
    text = (system_dir / problem / "system.txt").read_text()
    vars_match = re.search(r"Variables:\s*\[(.*?)\]", text, re.S)
    eqs_match = re.search(r"Equations?:\s*(.*?)(?=\n\s*\n\s*Measured)", text, re.S | re.I)
    measured_match = re.search(r"Measured Variables:\s*\[(.*?)\]", text, re.S | re.I)
    target_match = re.search(r"Target Polynomial:?\s*(.*)$", text, re.S | re.I)
    if not (vars_match and eqs_match and measured_match and target_match):
        raise RuntimeError(f"Could not parse system file for {problem}")
    variables = [v.strip().strip('"').strip("'") for v in vars_match.group(1).split(",") if v.strip()]
    equations = [ln.strip() for ln in eqs_match.group(1).splitlines() if ln.strip()]
    measured = [v.strip().strip('"').strip("'") for v in measured_match.group(1).split(",") if v.strip()]
    targets = [ln.strip() for ln in target_match.group(1).splitlines() if ln.strip()]
    removal_count = min(len(equations), axiom_limits.get(problem, len(equations)))
    for zero_index in range(removal_count):
        cases.append(
            {
                "problem": problem,
                "variables": variables,
                "measured_vars": measured,
                "targets": targets,
                "remaining_axioms": [axiom for i, axiom in enumerate(equations) if i != zero_index],
                "removed_indices": [zero_index + 1],
                "removed_axioms": [equations[zero_index]],
                "nonzero_factors": [],
                "status": "ok",
                "num_accepted": 0,
                "accepted": [],
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
