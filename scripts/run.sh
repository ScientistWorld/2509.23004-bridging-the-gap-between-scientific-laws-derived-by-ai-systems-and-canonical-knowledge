#!/bin/bash
# Hardening iteration 12, job 2.  Resumable (evaluator caches); safe to rerun
# after preemption.
#
#   1. held-out multiple-consequence instances: built in eval/test if missing
#      (all other instances stay byte-identical); a copy of the evaluator-private
#      files is kept in a gitignored backup so that a run killed while they are
#      off disk can be resumed;
#   2. oracle smoke check on every instance of both slices;
#   3. hidden test: the gym's solvers (reference + baselines) on all four
#      experiments from the final code -> scoring/scores_test.json;
#   4. hardening: reference draws, honest variants, a binomial brute-force probe
#      and a shortcut probe on the new experiment; key variants and the probe
#      on all experiments;
#   5. train: gym solvers -> scoring/scores_train.json (+ scores.json) and the
#      key variants on the new experiment.
set -u
cd /home/user
mkdir -p hardening/logs
BK=hardening/logs/private_backup
stamp() { echo "=== [$(date +%H:%M:%S)] $*"; }
restore_private() {
  if { [ ! -f eval/test/instances.json ] || [ ! -d eval/test/systems ]; } && [ -f $BK/test_private.tar.bak ]; then
    tar -xf $BK/test_private.tar.bak && echo "restored eval/test private files from backup"
  fi
}
save_private() { mkdir -p $BK && tar -cf $BK/test_private.tar.bak eval/test/instances.json eval/test/systems; }
count_mc() { python -c "import json,sys; print(sum(1 for i in json.load(open(sys.argv[1]))['instances'] if i.get('experiment')))" "$1" 2>/dev/null || echo 0; }

stamp environment
which Singular python
restore_private
[ -f eval/test/instances.json ] || python eval/test/build_instances.py || exit 1
[ -f eval/train/instances.json ] || python eval/train/build_instances.py || exit 1
if [ "$(count_mc eval/test/instances.json)" = "0" ]; then
  stamp "build held-out multiple-consequence instances"
  python eval/test/build_instances.py --mc-only || exit 1
fi
if [ "$(count_mc eval/train/instances.json)" = "0" ]; then
  python eval/train/build_instances.py --mc-only || exit 1
fi
save_private
python hardening/mc_report.py instances

stamp "oracle smoke check (all instances, both slices)"
python hardening/smoke_check.py > hardening/logs/smoke.log 2>&1
echo "smoke exit $?"; grep -E "oracle|SMOKE|NOT RECOVERED" hardening/logs/smoke.log | grep -v "^\[eval" | tail -30
restore_private

stamp "hidden test: gym solvers, all experiments"
bash scripts/evaluate_test.sh --cache-dir eval/test/_cache/iter12 --details-out eval/test/_runs/gym_details.json \
  2>&1 | grep -E "done in|Wrote|Error|Traceback|warning"
restore_private

stamp "hidden test: hardening solvers on the new experiment"
python eval/test/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc \
  --only reference_draw2 reference_draw3 reference_maxsets_4000 variant_bestfirst variant_bestfirst_sign \
         variant_bestfirst_saturate variant_saturation_only variant_saturation_bestfirst variant_sign_prior \
         bruteforce_binomial shortcut_observed_laws \
  --output hardening/scores_test_mc.json --details-out eval/test/_runs/mc_details.json \
  --cache-dir eval/test/_cache/iter12_mc 2>&1 | grep -E "done in|Wrote|Error|Traceback|warning"
restore_private
python hardening/mc_report.py summary scoring/scores_test.json eval/test/_runs/gym_details.json \
  hardening/scores_test_mc.json eval/test/_runs/mc_details.json

stamp "hidden test: reference draws, key variants and brute force on all experiments"
python eval/test/evaluate.py --solvers-dir hardening/solvers_mc \
  --only reference_draw2 reference_draw3 variant_bestfirst variant_bestfirst_sign variant_sign_prior bruteforce_binomial \
  --output hardening/scores_test_all.json --details-out eval/test/_runs/all_details.json \
  --cache-dir eval/test/_cache/iter12_mc 2>&1 | grep -E "done in|Wrote|Error|Traceback|warning"
restore_private

stamp "train: gym solvers, all experiments"
bash scripts/evaluate.sh --cache-dir eval/train/_cache/iter12 --details-out eval/train/_runs/gym_details.json \
  2>&1 | grep -E "done in|Wrote|Error|Traceback"

stamp "train: key variants on the new experiment"
python eval/train/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc \
  --only reference_draw2 variant_bestfirst variant_bestfirst_sign bruteforce_binomial \
  --output hardening/scores_train_mc.json --details-out eval/train/_runs/mc_details.json \
  --cache-dir eval/train/_cache/iter12_mc 2>&1 | grep -E "done in|Wrote|Error|Traceback"
python hardening/mc_report.py summary scoring/scores_train.json eval/train/_runs/gym_details.json \
  hardening/scores_train_mc.json eval/train/_runs/mc_details.json

stamp validate
python validate.py 2>&1 | tail -30
stamp done
