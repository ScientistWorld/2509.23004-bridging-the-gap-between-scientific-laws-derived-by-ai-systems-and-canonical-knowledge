#!/bin/bash
# Verification job, round 2 (CPU, no internet): run-to-run noise of the
# reference, determinism fixes, and honest variants that should beat it.
#
#   1. reference reruns from the gym solver (two more draws, fresh caches)
#   2. round-2 solvers twice / once on the held-out slice:
#        reference_no_aslr     the reference with Singular's address-space
#                              randomization disabled (determinism check)
#        variant_canonical     reduced Groebner basis of each prime as generators
#        variant_sign_prior    drop sign twins that cannot hold with positive
#                              quantities and rank them last
#        variant_dim_rank      top-dimensional components first (Theorem 1)
#        variant_sign_dim_restate  sign prior + dimension rank + drop target
#                              restatements
#   3. reference_no_aslr and variant_sign_prior on the train slice
#   4. determinism report, rank diagnostics with paired comparisons, validate.py
set -u
cd /home/user
LOG=hardening/logs
mkdir -p "$LOG" eval/test/_runs eval/train/_runs
stage () { echo "=== [$(date +%H:%M:%S)] $*"; }

stage "environment"
python --version
command -v setarch && setarch "$(uname -m)" -R true && echo "setarch -R works"

stage "reference reruns (test)"
for run in 2 3; do
  python eval/test/evaluate.py --solvers-dir scripts/solvers --only ai_noether_exact \
    --output hardening/scores_test_reference_run$run.json --cache-dir eval/test/_cache/final$run \
    --details-out eval/test/_runs/reference_run${run}_details.json > "$LOG/eval_reference_run$run.log" 2>&1
  echo "exit $?"; grep -E "done in|Wrote|warning" "$LOG/eval_reference_run$run.log"
done

stage "round-2 solvers, draw a (test)"
python eval/test/evaluate.py --solvers-dir hardening/solvers_round2 \
  --output hardening/scores_test_round2_a.json --cache-dir eval/test/_cache/round2_a \
  --details-out eval/test/_runs/round2_a_details.json > "$LOG/eval_round2_a.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote|warning" "$LOG/eval_round2_a.log"

stage "round-2 solvers, draw b (test)"
python eval/test/evaluate.py --solvers-dir hardening/solvers_round2 \
  --only reference_no_aslr variant_canonical variant_sign_prior \
  --output hardening/scores_test_round2_b.json --cache-dir eval/test/_cache/round2_b \
  --details-out eval/test/_runs/round2_b_details.json > "$LOG/eval_round2_b.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote|warning" "$LOG/eval_round2_b.log"

stage "round-2 solvers (train)"
python eval/train/evaluate.py --solvers-dir hardening/solvers_round2 \
  --only reference_no_aslr variant_sign_prior \
  --output hardening/scores_train_round2.json --cache-dir eval/train/_cache/round2 \
  --details-out eval/train/_runs/round2_details.json > "$LOG/eval_train_round2.log" 2>&1
echo "exit $?"; grep -E "done in|Wrote" "$LOG/eval_train_round2.log"

stage "determinism"
python hardening/check_instances.py pairs
git status --short eval/test | head

stage "summary"
python hardening/summarize.py | tee "$LOG/summary.txt"

stage "validate"
python validate.py || true
stage "done"
