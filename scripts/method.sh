#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

python method/exact_abduction_runner.py \
  --problems \
    decay \
    escape_velocity \
    hagen \
    hall \
    inelastic_relativistic_collision \
    kepler \
    light \
    photoHall \
    relativistic_laws \
    simple_harmonic_oscillator \
    time_dilation \
    compton \
  --sizes 1 \
  --max-candidate-size 1 \
  --axiom-limits hall=7 \
  --timeout-decomposition 120 \
  --timeout-case 120 \
  --output scoring/ai_noether_exact_outputs.json

bash scripts/evaluate.sh scoring/ai_noether_exact_outputs.json
