#!/bin/bash
# Regenerate the reproduction artifacts from the current method code, then
# validate the official and split score files.

set -e

cd /home/user

bash scripts/reproduce.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
python validate.py --compare
