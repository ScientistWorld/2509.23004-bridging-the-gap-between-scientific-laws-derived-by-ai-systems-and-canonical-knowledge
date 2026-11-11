#!/bin/bash
# Reproduce the gym end to end inside the container (CPU only, no internet):
#   1. build train/test instances if missing (Singular checks),
#   2. run every solver in scripts/solvers/ on the train slice (paper systems),
#   3. run the hidden-test evaluation on the held-out slice.
set -e
cd "$(dirname "$0")/.."
bash scripts/evaluate.sh
bash scripts/evaluate_test.sh
