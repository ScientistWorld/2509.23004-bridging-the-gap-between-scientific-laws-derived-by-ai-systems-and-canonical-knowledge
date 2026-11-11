#!/bin/bash
# Verification job for the hardening fixes (CPU, no internet).
#
#   1. rebuild train/test instances (stripped-target nontriviality check,
#      saturated complete theory for the soundness test); prune cached solver
#      outputs whose inputs changed
#   2. smoke: the oracle must score perfectly on every instance of both slices,
#      a contradiction and a stripped target must earn nothing
#   3. hidden test, gym solvers rerun from the final code (fresh cache)
#        -> scoring/scores_test.json; determinism check against the previous run
#   4. shortcuts (no cache) and honest variants (cached outputs, rescored)
#   5. train slice, gym solvers from the final code -> scores_train.json, scores.json;
#      two honest variants on train for the train/test comparison
#   6. subset probes (duplicates, timeout, full-budget brute force), rank
#      diagnostics with paired comparisons, validate.py
# Per-instance details stay under eval/*/_runs and caches under eval/*/_cache
# (both gitignored).
set -u
cd /home/user
LOG=hardening/logs
mkdir -p "$LOG" eval/test/_runs eval/train/_runs
stage () { echo "=== [$(date +%H:%M:%S)] $*"; }

stage "environment"
python --version
command -v Singular
echo 'print(system("version")); quit;' | Singular -q || true

stage "rebuild instances"
python eval/test/build_instances.py --output eval/test/instances.json > "$LOG/build_test.log" 2>&1 \
  || { cat "$LOG/build_test.log"; exit 1; }
cat "$LOG/build_test.log"
python eval/train/build_instances.py --output eval/train/instances.json > "$LOG/build_train.log" 2>&1 \
  || { cat "$LOG/build_train.log"; exit 1; }
cat "$LOG/build_train.log"
python hardening/check_instances.py prune

stage "smoke check"
python hardening/smoke_check.py > "$LOG/smoke.log" 2>&1
smoke=$?
grep -E "oracle|contradiction|stripped_target|ORACLE NOT|SMOKE" "$LOG/smoke.log" | cut -c1-400 | head -n 80
if [ "$smoke" -eq 2 ]; then echo "SMOKE: pipeline broken, stopping"; exit 1; fi

stage "hidden test: gym solvers from the final code"
bash scripts/evaluate_test.sh --cache-dir eval/test/_cache/final \
  --details-out eval/test/_runs/gym_details.json > "$LOG/eval_test.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote|warning" "$LOG/eval_test.log"
python hardening/check_instances.py determinism

stage "hardening: shortcuts (no cache)"
FORGE_PATH=hardening/scores_test_shortcuts.json python eval/test/evaluate.py \
  --solvers-dir hardening/solvers_shortcuts --output hardening/scores_test_shortcuts.json \
  --details-out eval/test/_runs/shortcuts_details.json > "$LOG/eval_shortcuts.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote|warning" "$LOG/eval_shortcuts.log"

stage "hardening: honest variants (cached outputs rescored)"
python eval/test/evaluate.py --solvers-dir hardening/solvers_variants \
  --output hardening/scores_test_variants.json --cache-dir eval/test/_cache/variants \
  --details-out eval/test/_runs/variants_details.json > "$LOG/eval_variants.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_variants.log"

stage "train: gym solvers from the final code"
bash scripts/evaluate.sh --cache-dir eval/train/_cache/final \
  --details-out eval/train/_runs/gym_details.json > "$LOG/eval_train.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_train.log"
python eval/train/evaluate.py --solvers-dir hardening/solvers_variants \
  --only variant_extra_orders variant_saturation_only \
  --output hardening/scores_train_variants.json --cache-dir eval/train/_cache/variants \
  --details-out eval/train/_runs/variants_details.json > "$LOG/eval_train_variants.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_train_variants.log"

stage "hardening: subset probes"
python eval/test/evaluate.py --solvers-dir hardening/solvers_dupe --max-instances 8 \
  --output hardening/scores_test_dupe_max_instances8.json --cache-dir eval/test/_cache/dupe \
  > "$LOG/eval_dupe.log" 2>&1
python eval/test/evaluate.py --solvers-dir scripts/solvers --only ai_noether_exact --max-instances 8 \
  --output hardening/scores_test_reference_max_instances8.json --cache-dir eval/test/_cache/final \
  > "$LOG/eval_reference_subset.log" 2>&1
python eval/test/evaluate.py --solvers-dir hardening/solvers_timeout --max-instances 1 \
  --output hardening/scores_test_timeout_max_instances1.json > "$LOG/eval_timeout.log" 2>&1
python eval/test/evaluate.py --solvers-dir hardening/solvers_bruteforce --max-instances 12 \
  --output hardening/scores_test_bruteforce_max_instances12.json --cache-dir eval/test/_cache/brute \
  > "$LOG/eval_bruteforce.log" 2>&1
python eval/test/evaluate.py --solvers-dir scripts/solvers --only ai_noether_exact --max-instances 12 \
  --output hardening/scores_test_reference_max_instances12.json --cache-dir eval/test/_cache/final \
  > "$LOG/eval_reference_subset12.log" 2>&1
echo "exit $?"
git status --short eval/test | head

stage "summary"
python hardening/summarize.py | tee "$LOG/summary.txt"

stage "validate"
python validate.py || true
stage "done"
