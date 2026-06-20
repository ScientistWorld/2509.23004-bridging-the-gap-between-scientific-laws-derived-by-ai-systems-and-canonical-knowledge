#!/bin/bash
# Targeted CPU reproduction job for the exact symbolic AI-Noether core claims.

set -e

cd /home/user

bash scripts/baseline.sh

python method/exact_abduction_runner.py \
  --problems simple_harmonic_oscillator kepler \
  --sizes 1 \
  --max-candidate-size 1 \
  --timeout-decomposition 300 \
  --timeout-case 600 \
  --output scoring/ai_noether_core_outputs.json

python method/exact_abduction_runner.py \
  --problems kepler \
  --sizes 2,3 \
  --filter-degenerate \
  --timeout-decomposition 120 \
  --timeout-case 120 \
  --output scoring/ai_noether_kepler_multi_outputs.json

bash scripts/evaluate.sh --include-multi \
  scoring/baseline_outputs.json \
  scoring/ai_noether_core_outputs.json \
  scoring/ai_noether_kepler_multi_outputs.json

python validate.py --compare
