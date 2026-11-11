#!/bin/bash
# Visible train evaluation on the paper's twelve public benchmark theories.
#
# Runs every solver found in scripts/solvers/*.sh on the train instances in
# eval/train/instances.json (rebuilt from data/systems_and_phenomena if absent)
# and writes scoring/scores_train.json with one row per solver per experiment.
#
# Optional flags: --only NAME [NAME ...] re-evaluates selected solvers and merges
# them into the existing file; --max-instances N gives a quick smoke run;
# --cache-dir DIR resumes an interrupted run.
set -e
cd "$(dirname "$0")/.."
python eval/train/evaluate.py "$@"
