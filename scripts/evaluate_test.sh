#!/bin/bash
# Hidden-test evaluation.  Run with no arguments.
#
# Runs every solver found in scripts/solvers/*.sh on the held-out instances that
# live only in eval/test/ (built there from theories that never leave eval/test),
# under the fixed per-instance time limit, and recomputes every metric from the
# candidate polynomials the solver writes.  Writes scoring/scores_test.json with
# one row per solver in every experiment.
#
# Optional development flags (not used by the hidden test) are passed through,
# e.g. --cache-dir DIR to resume an interrupted run.
set -e
cd "$(dirname "$0")/.."
python eval/test/evaluate.py "$@"
