#!/bin/bash
# Run the train/test split evaluators over every saved method-output artifact.

set -e

cd /home/user

bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
