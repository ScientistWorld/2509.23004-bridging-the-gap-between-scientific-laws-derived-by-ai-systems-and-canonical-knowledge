#!/bin/bash
# Hardening iteration 12, job 3: redesigned multiple-consequence experiment
# (identifiable removals of 2-5 axioms).  Resumable (evaluator caches); safe to
# rerun after preemption.
#
#   1. rebuild the multiple-consequence instances on both slices (all other
#      instances stay byte-identical); keep a gitignored backup of the
#      evaluator-private files so a run killed while they are off disk resumes;
#   2. oracle smoke check on the new instances;
#   3. reference draws, the baselines, honest search variants, the binomial
#      brute-force probe and a shortcut probe on the new experiment (test, train).
set -u
cd /home/user
mkdir -p hardening/logs
BK=hardening/logs/private_backup
MARK=hardening/logs/mc_v2_built
stamp() { echo "=== [$(date +%H:%M:%S)] $*"; }
restore_private() {
  if { [ ! -f eval/test/instances.json ] || [ ! -d eval/test/systems ]; } && [ -f $BK/test_private.tar.bak ]; then
    tar -xf $BK/test_private.tar.bak && echo "restored eval/test private files from backup"
  fi
}
save_private() { mkdir -p $BK && tar -cf $BK/test_private.tar.bak eval/test/instances.json eval/test/systems; }

stamp environment
which Singular python
restore_private
if [ ! -f $MARK ]; then
  stamp "rebuild multiple-consequence instances (identifiable removals, 2-5 axioms)"
  python eval/test/build_instances.py --mc-only || exit 1
  python eval/train/build_instances.py --mc-only || exit 1
  save_private
  touch $MARK
fi
python hardening/mc_report.py instances

stamp "oracle smoke check (multiple consequences)"
python hardening/smoke_check.py --experiments multiple_consequences > hardening/logs/smoke_mc.log 2>&1
echo "smoke exit $?"; grep -E "oracle|SMOKE|NOT RECOVERED" hardening/logs/smoke_mc.log | grep -v "^\[eval" | tail -12
restore_private

SOLVERS="ai_noether_exact reference_draw2 reference_maxsets_4000 variant_bestfirst variant_bestfirst_sign \
  variant_greedy variant_greedy_sign variant_greedy_only bruteforce_binomial enumerative_baseline \
  no_abduction_baseline shortcut_observed_laws"
stamp "hidden test: multiple consequences"
python eval/test/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc --only $SOLVERS \
  --output hardening/scores_test_mc2.json --details-out eval/test/_runs/mc2_details.json \
  --cache-dir eval/test/_cache/iter12_mc2 2>&1 | grep -E "done in|Wrote|Error|Traceback|warning"
restore_private
python hardening/mc_report.py summary hardening/scores_test_mc2.json eval/test/_runs/mc2_details.json

stamp "train: multiple consequences"
python eval/train/evaluate.py --experiments multiple_consequences --solvers-dir hardening/solvers_mc --only $SOLVERS \
  --output hardening/scores_train_mc2.json --details-out eval/train/_runs/mc2_details.json \
  --cache-dir eval/train/_cache/iter12_mc2 2>&1 | grep -E "done in|Wrote|Error|Traceback"
python hardening/mc_report.py summary hardening/scores_train_mc2.json eval/train/_runs/mc2_details.json
stamp done
