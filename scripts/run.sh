#!/bin/bash
# Reproduce the gym's reference end to end (CPU, no internet).
#
#   1. build the train and held-out instances if missing (Singular checks of
#      well-posedness; saturated complete theories for the soundness test);
#   2. train slice: run every solver in scripts/solvers/ (the AI-Noether
#      reference and the two baselines) -> scoring/scores_train.json, scores.json;
#   3. hidden test: the same solvers on the held-out instances
#      -> scoring/scores_test.json;
#   4. validate.
# The hardening audit (shortcuts, variants, noise draws) is described in
# HARDENING.md; its probes live under hardening/.
set -e
cd /home/user
[ -f eval/train/instances.json ] || python eval/train/build_instances.py
[ -f eval/test/instances.json ] || python eval/test/build_instances.py
bash scripts/evaluate.sh
bash scripts/evaluate_test.sh
python validate.py
