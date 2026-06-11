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
  --problems kepler \
  --sizes 2,3 \
  --saturate-nondegenerate \
  --timeout-decomposition 120 \
  --timeout-case 120 \
  --output scoring/ai_noether_kepler_multi_outputs.json

bash scripts/evaluate.sh --include-multi \
  scoring/ai_noether_exact_outputs.json \
  scoring/ai_noether_kepler_multi_outputs.json
python validate.py --compare
