#!/bin/bash
# Reproduce the gym's reference end to end and run the hardening checks
# (CPU, no internet).  Resumable: evaluator caches let a preempted run continue.
#
#   1. instances: the train and held-out instances are built if missing (they are
#      committed; a gitignored backup of the evaluator-private files lets a run
#      killed while they are off disk resume);
#   2. oracle smoke check: every instance of both slices is solvable;
#   3. hidden test: the gym's solvers (reference + baselines) on all four
#      experiments -> scoring/scores_test.json;
#   4. hardening on the hidden test: reference redraws, the reference with the
#      earlier 400-subset budget and with a 5x budget, better and weaker
#      variants, the binomial brute-force probe, and every shortcut probe;
#   5. train: gym solvers -> scoring/scores_train.json (+ scores.json) and the
#      main variants;
#   6. rank summaries (hardening/summary_final.json, hardening/summary_train.json)
#      and validation.
set -u
cd /home/user
mkdir -p hardening/logs
BK=hardening/logs/private_backup
stamp() { echo "=== [$(date +%H:%M:%S)] $*"; }
restore_private() {
  if { [ ! -f eval/test/instances.json ] || [ ! -d eval/test/systems ] || [ ! -d eval/test/systems_mc ]; } \
     && [ -f $BK/test_private_v3.tar.bak ]; then
    tar -xf $BK/test_private_v3.tar.bak && echo "restored eval/test private files from backup"
  fi
}
filter() { grep -E "done in|Wrote|Error|Traceback|warning"; }
df -h /home/user | tail -1

stamp environment
which Singular python
restore_private
[ -f eval/test/instances.json ] || python eval/test/build_instances.py || exit 1
[ -f eval/train/instances.json ] || python eval/train/build_instances.py || exit 1
python hardening/mc_report.py instances

stamp "oracle smoke check (every instance, both slices)"
python hardening/smoke_check.py > hardening/logs/smoke.log 2>&1
echo "smoke exit $?"; grep -E " oracle |SMOKE|NOT RECOVERED" hardening/logs/smoke.log | grep -v "^\[eval" | tail -12
restore_private

stamp "hidden test: gym solvers, all experiments"
bash scripts/evaluate_test.sh --cache-dir eval/test/_cache/iter13_final --details-out eval/test/_runs/gym_details.json 2>&1 | filter
restore_private

stamp "hidden test: reference draws, budgets, variants, weaker variants and brute force"
python eval/test/evaluate.py --solvers-dir hardening/solvers_mc \
  --only reference_draw2 reference_draw3 reference_maxsets_400 reference_maxsets_20000 \
         variant_sign_prior variant_bestfirst_sign variant_greedy_sign variant_sparse variant_sparse_sign \
         variant_saturation_only weaker_no_reasoning weaker_unranked_singletons bruteforce_binomial \
  --output hardening/scores_test_variants_final.json --details-out eval/test/_runs/variants_final_details.json \
  --cache-dir eval/test/_cache/iter13_h 2>&1 | filter
restore_private

stamp "hidden test: shortcut probes, all experiments"
# FORGE_PATH: the forged-score shortcut writes there; the evaluator then overwrites it
FORGE_PATH=hardening/scores_test_shortcuts_final.json python eval/test/evaluate.py --solvers-dir hardening/solvers_shortcuts \
  --output hardening/scores_test_shortcuts_final.json --details-out eval/test/_runs/shortcuts_final_details.json \
  --cache-dir eval/test/_cache/iter13_s 2>&1 | filter
python eval/test/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc \
  --only shortcut_observed_laws \
  --output hardening/scores_test_mc_final.json --details-out eval/test/_runs/mc_final_details.json \
  --cache-dir eval/test/_cache/iter13_s 2>&1 | filter
restore_private

stamp "train: gym solvers, all experiments"
bash scripts/evaluate.sh --cache-dir eval/train/_cache/iter13_final --details-out eval/train/_runs/gym_details.json 2>&1 | filter

stamp "train: variants, all experiments"
python eval/train/evaluate.py --solvers-dir hardening/solvers_mc \
  --only reference_maxsets_400 variant_sign_prior variant_sparse_sign weaker_no_reasoning bruteforce_binomial \
  --output hardening/scores_train_variants_final.json --details-out eval/train/_runs/variants_final_details.json \
  --cache-dir eval/train/_cache/iter13_h 2>&1 | filter

stamp "summaries"
python hardening/mc_report.py summary scoring/scores_test.json eval/test/_runs/gym_details.json \
  hardening/scores_test_variants_final.json eval/test/_runs/variants_final_details.json
python hardening/rank.py --out hardening/summary_final.json \
  hardening/scores_test_variants_final.json:eval/test/_runs/variants_final_details.json \
  hardening/scores_test_mc_final.json:eval/test/_runs/mc_final_details.json \
  hardening/scores_test_shortcuts_final.json:eval/test/_runs/shortcuts_final_details.json
python hardening/rank.py --slice train --out hardening/summary_train.json \
  hardening/scores_train_variants_final.json:eval/train/_runs/variants_final_details.json

stamp validate
python validate.py 2>&1 | tail -25
stamp done
