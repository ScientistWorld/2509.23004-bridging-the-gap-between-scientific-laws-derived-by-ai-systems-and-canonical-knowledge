#!/bin/bash
# Run the baselines on the train instances through the evaluator:
#   no_abduction_baseline  proposes nothing (incomplete theory kept as is)
#   enumerative_baseline   syntax-guided enumeration of small binomial axioms
#                          (stand-in for the paper's solver-based SyGuS baseline)
set -e
cd "$(dirname "$0")/.."
python eval/train/evaluate.py --only no_abduction_baseline enumerative_baseline "$@"
