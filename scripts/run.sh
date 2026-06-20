#!/bin/bash
# CPU validation job for the stricter evaluator and data-separated benchmark assets.

set -e

cd /home/user

bash scripts/baseline.sh

python eval/merge_outputs.py \
  --input scoring/ai_noether_exact_outputs.json scoring/rational_smoke_outputs.json \
  --output scoring/ai_noether_merged_outputs.json

bash scripts/evaluate.sh --include-multi \
  scoring/baseline_outputs.json \
  scoring/ai_noether_merged_outputs.json \
  scoring/ai_noether_kepler_multi_outputs.json

python validate.py --compare
