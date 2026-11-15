#!/bin/bash
# Hardening iteration 12, job 1 (exploration of the new multiple-consequence
# experiment).  Builds the multiple-consequence instances on both slices (all
# other instances stay byte-identical), checks with the oracle that every new
# instance is solvable, and runs the reference (several draws), honest search
# variants, a binomial brute-force probe, the baselines and a shortcut probe on
# the new experiment.  The final reproduction run.sh is restored afterwards.
set -u
cd /home/user
mkdir -p hardening/logs
stamp() { echo "=== [$(date +%H:%M:%S)] $*"; }

stamp environment
which Singular python
python --version

stamp "build multiple-consequence instances"
python eval/test/build_instances.py --mc-only || exit 1
python eval/train/build_instances.py --mc-only || exit 1
python hardening/mc_report.py instances

stamp "oracle smoke check (multiple consequences)"
python hardening/smoke_check.py --experiments multiple_consequences 2>&1 | grep -v "^test probe\|^train probe" | tail -40

stamp "test: multiple consequences"
python eval/test/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc \
  --output hardening/scores_test_mc_explore.json --details-out eval/test/_runs/mc_explore_details.json \
  --cache-dir eval/test/_cache/mc_explore 2>&1 | grep -E "done in|Wrote|Error|Traceback"
python hardening/mc_report.py summary hardening/scores_test_mc_explore.json eval/test/_runs/mc_explore_details.json

stamp "train: multiple consequences"
python eval/train/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc \
  --only ai_noether_exact reference_draw2 variant_bestfirst variant_bestfirst_sign variant_saturation_bestfirst \
         bruteforce_binomial enumerative_baseline no_abduction_baseline \
  --output hardening/scores_train_mc_explore.json --details-out eval/train/_runs/mc_explore_details.json \
  --cache-dir eval/train/_cache/mc_explore 2>&1 | grep -E "done in|Wrote|Error|Traceback"
python hardening/mc_report.py summary hardening/scores_train_mc_explore.json eval/train/_runs/mc_explore_details.json

stamp done
