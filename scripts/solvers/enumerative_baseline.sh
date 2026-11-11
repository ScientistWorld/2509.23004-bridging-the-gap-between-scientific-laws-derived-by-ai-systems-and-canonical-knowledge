#!/bin/bash
# Baseline: syntax-guided enumeration of small binomial axioms (brute force).
set -e
cd "$(dirname "$(readlink -f "$0")")/../.."
exec python baseline/enumerative_abduction.py --instance "$1" --output "$2"
