#!/bin/bash
# Evaluation entry point for the paper-level reproduction.
#
# The paper's own benchmark (its twelve public theories) is the train slice, so
# this runs the train evaluator on every solver in scripts/solvers/ and also
# writes the result to scoring/scores.json.  The evaluator never imports
# method/: it calls each solver through scripts/solvers/<name>.sh and scores the
# candidate polynomials it writes.  Extra flags are passed to the evaluator.
set -e
cd "$(dirname "$0")/.."
python eval/train/evaluate.py "$@"
cp scoring/scores_train.json scoring/scores.json
echo "Wrote scoring/scores.json"
