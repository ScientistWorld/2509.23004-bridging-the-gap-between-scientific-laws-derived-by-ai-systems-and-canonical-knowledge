#!/bin/bash
# Iteration 12, job 5: finish the train slice of the end-to-end run (the previous
# job's train step failed on a full shared filesystem).  Resumes from the train
# caches of that job; the held-out test results of that job are final.
set -u
cd /home/user
stamp() { echo "=== [$(date +%H:%M:%S)] $*"; }
filter() { grep -E "done in|Wrote|Error|Traceback|warning"; }
df -h /home/user | tail -1

stamp "train: gym solvers, all experiments"
bash scripts/evaluate.sh --cache-dir eval/train/_cache/iter12_final --details-out eval/train/_runs/gym_details.json 2>&1 | filter

stamp "train: variants, all experiments"
python eval/train/evaluate.py --solvers-dir hardening/solvers_mc \
  --only reference_draw2 variant_sign_prior variant_sparse_sign bruteforce_binomial \
  --output hardening/scores_train_variants_final.json --details-out eval/train/_runs/variants_final_details.json \
  --cache-dir eval/train/_cache/iter12_final_h 2>&1 | filter

stamp "summaries"
python hardening/mc_report.py summary scoring/scores_train.json eval/train/_runs/gym_details.json \
  hardening/scores_train_variants_final.json eval/train/_runs/variants_final_details.json \
  hardening/scores_train_mc_final.json eval/train/_runs/mc_final_details.json
stamp validate
python validate.py 2>&1 | tail -25
stamp done
