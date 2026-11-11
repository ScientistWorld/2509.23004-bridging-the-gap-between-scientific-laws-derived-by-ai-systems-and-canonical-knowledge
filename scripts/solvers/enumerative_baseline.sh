#!/bin/bash
# Baseline: syntax-guided enumeration of small binomial axioms (brute force).
# Tests the first 6000 grammar candidates (deterministic); the 50 s budget is
# only a safety stop below the evaluator's time limit.
set -e
cd "$(dirname "$(readlink -f "$0")")/../.."
export ENUM_MAX_CANDIDATES=6000
export ENUM_BUDGET=50
exec python baseline/enumerative_abduction.py --instance "$1" --output "$2"
