#!/bin/bash
# Example job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available
#   - No internet access
#
# Make sure all data, code, and dependencies are already in the
# workspace or baked into the container before submitting.

set -e

cd /home/user

python method/exact_abduction_runner.py \
  --problems \
    escape_velocity \
    inelastic_relativistic_collision \
    light \
    relativistic_laws \
    simple_harmonic_oscillator \
    time_dilation \
  --sizes 1 \
  --max-candidate-size 1 \
  --timeout-decomposition 180 \
  --timeout-case 180 \
  --output scoring/rational_smoke_outputs.json

python eval/evaluate_exact.py \
  --input scoring/rational_smoke_outputs.json \
  --output scoring/rational_smoke_scores.json

python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("scoring/rational_smoke_outputs.json").read_text())
fraction_errors = [
    (case["problem"], case["removed_indices"], case.get("error", ""))
    for case in payload["cases"]
    if "expected an integer" in case.get("error", "")
]
if fraction_errors:
    raise SystemExit(f"fraction coefficient failures remain: {fraction_errors}")
print("Rational-coefficient smoke test passed without integer-domain errors.")
PY
