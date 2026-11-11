#!/bin/bash
# Reference solver: AI-Noether exact Encode-Decompose-Reason (method/).
# Called by the evaluators as:  bash scripts/solvers/ai_noether_exact.sh <instance.json> <output.json>
# The per-instance time budget arrives in $ABDUCTION_TIME_LIMIT (seconds).
set -e
cd "$(dirname "$(readlink -f "$0")")/../.."
exec python method/exact_abduction_runner.py --instance "$1" --output "$2"
