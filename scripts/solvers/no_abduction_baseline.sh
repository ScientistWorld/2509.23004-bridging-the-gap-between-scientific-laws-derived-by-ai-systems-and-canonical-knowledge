#!/bin/bash
# Baseline: propose no axioms (the incomplete theory is left unchanged).
set -e
cd "$(dirname "$(readlink -f "$0")")/../.."
exec python baseline/no_abduction.py "$1" "$2"
