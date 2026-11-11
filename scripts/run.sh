#!/bin/bash
# Verification job for the hardened gym (CPU, no internet).
#
# Stages (each resumable through the evaluator's --cache-dir):
#   1. build the held-out and train instances (Singular well-posedness checks)
#   2. fail-fast smoke check (oracle must score perfectly, contradiction must fail)
#   3. hidden test with the gym's solvers  -> scoring/scores_test.json
#   4. hardening probes on the hidden test: shortcuts, honest variants,
#      duplicate-set and timeout probes, full-budget brute force (subset)
#   5. train evaluation (paper's twelve theories) -> scoring/scores_train.json, scores.json
#   6. rank diagnostics and validate.py
# Per-instance details of the held-out slice stay under eval/test/_runs (gitignored).
set -u
cd /home/user
LOG=hardening/logs
mkdir -p "$LOG" eval/test/_runs eval/train/_runs
stage () { echo "=== [$(date +%H:%M:%S)] $*"; }

stage "environment"
python --version
echo 'print(system("version")); quit;' | Singular -q || true

stage "build held-out instances"
if [ ! -f eval/test/instances.json ]; then
  python eval/test/build_instances.py > "$LOG/build_test.log" 2>&1 || { cat "$LOG/build_test.log"; exit 1; }
fi
tail -n 20 "$LOG/build_test.log" 2>/dev/null

stage "smoke check"
python hardening/smoke_check.py > "$LOG/smoke.log" 2>&1
smoke=$?
tail -n 60 "$LOG/smoke.log"
[ "$smoke" -eq 0 ] || { echo "SMOKE FAILED"; exit 1; }

stage "hidden test with gym solvers"
bash scripts/evaluate_test.sh --cache-dir eval/test/_cache/gym \
  --details-out eval/test/_runs/gym_details.json > "$LOG/eval_test.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_test.log"

stage "hardening: shortcuts"
FORGE_PATH=hardening/scores_test_shortcuts.json python eval/test/evaluate.py \
  --solvers-dir hardening/solvers_shortcuts --output hardening/scores_test_shortcuts.json \
  --cache-dir eval/test/_cache/shortcuts --details-out eval/test/_runs/shortcuts_details.json \
  > "$LOG/eval_shortcuts.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_shortcuts.log"

stage "hardening: honest variants"
python eval/test/evaluate.py --solvers-dir hardening/solvers_variants \
  --output hardening/scores_test_variants.json --cache-dir eval/test/_cache/variants \
  --details-out eval/test/_runs/variants_details.json > "$LOG/eval_variants.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_variants.log"

stage "build train instances"
if [ ! -f eval/train/instances.json ]; then
  python eval/train/build_instances.py > "$LOG/build_train.log" 2>&1 || cat "$LOG/build_train.log"
fi
tail -n 20 "$LOG/build_train.log" 2>/dev/null

stage "train evaluation with gym solvers"
bash scripts/evaluate.sh --cache-dir eval/train/_cache/gym \
  --details-out eval/train/_runs/gym_details.json > "$LOG/eval_train.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_train.log"

stage "hardening: duplicate-set and timeout probes (subsets)"
python eval/test/evaluate.py --solvers-dir hardening/solvers_dupe --max-instances 8 \
  --output hardening/scores_test_dupe_max_instances8.json --cache-dir eval/test/_cache/dupe \
  > "$LOG/eval_dupe.log" 2>&1
python eval/test/evaluate.py --solvers-dir scripts/solvers --only ai_noether_exact --max-instances 8 \
  --output hardening/scores_test_reference_max_instances8.json --cache-dir eval/test/_cache/gym \
  > "$LOG/eval_reference_subset.log" 2>&1
python eval/test/evaluate.py --solvers-dir hardening/solvers_timeout --max-instances 1 \
  --output hardening/scores_test_timeout_max_instances1.json > "$LOG/eval_timeout.log" 2>&1
echo "exit $?"

stage "hardening: brute force with the full time limit (subset)"
python eval/test/evaluate.py --solvers-dir hardening/solvers_bruteforce --max-instances 12 \
  --output hardening/scores_test_bruteforce_max_instances12.json --cache-dir eval/test/_cache/brute \
  > "$LOG/eval_bruteforce.log" 2>&1
python eval/test/evaluate.py --solvers-dir scripts/solvers --only ai_noether_exact --max-instances 12 \
  --output hardening/scores_test_reference_max_instances12.json --cache-dir eval/test/_cache/gym \
  > "$LOG/eval_reference_subset12.log" 2>&1
echo "exit $?"

stage "summary"
python hardening/summarize.py | tee "$LOG/summary.txt"

stage "validate"
python validate.py || true
stage "done"
