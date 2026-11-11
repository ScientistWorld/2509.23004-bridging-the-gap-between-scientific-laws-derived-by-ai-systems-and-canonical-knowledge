#!/bin/bash
# Run the paper's method (AI-Noether exact Encode-Decompose-Reason) on the
# train instances through the evaluator.  The method needs no training: the
# solver scripts/solvers/ai_noether_exact.sh is run once per instance.
set -e
cd "$(dirname "$0")/.."
python eval/train/evaluate.py --only ai_noether_exact "$@"
