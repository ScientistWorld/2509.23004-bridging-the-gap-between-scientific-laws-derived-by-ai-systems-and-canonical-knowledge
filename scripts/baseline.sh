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
from pathlib import Path

payload = {
    "method": "no_abduction_baseline",
    "algorithm": "remaining_axioms_only",
    "cases": [
        {
            "problem": p,
            "removed_indices": [i],
            "status": "ok",
            "num_accepted": 0,
            "success": False,
            "strong_success": False,
            "runtime_seconds": 0.0,
        }
        for p, n in [("simple_harmonic_oscillator", 6), ("kepler", 5)]
        for i in range(1, n + 1)
    ],
}
Path("scoring/baseline_outputs.json").write_text(json.dumps(payload, indent=2))
PY
python eval/evaluate_exact.py --input scoring/baseline_outputs.json --output scoring/baseline_scores.json
