#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script must be SELF-CONTAINED using only code in eval/.
# Do NOT import from method/ — evaluate.sh must work even when the
# paper's method code is hidden from a scientist agent.
#
# Design it so that anyone following the same output format can run
# this script to evaluate their results.
#
# OUTPUT CONTRACT: This script MUST write scoring/scores.json containing
# a JSON dict nested by experiment, e.g.:
#   {"imagenet_classification": {"top1_accuracy": 82.1, "top5_accuracy": 94.8}}
# Experiment and metric names must match the keys in scoring/reference.json.
# This file is read by the system for automated comparison.
#
# Example usage:
#   ./evaluate.sh <method_and_run_name>                             # evaluate with defaults
#   ./evaluate.sh <method_and_run_name> checkpoints/epoch_10.pt     # evaluate a specific checkpoint
#
# Called from run.sh after training, or independently.

set -e

cd /home/user

mkdir -p scoring

include_multi=0
if [ "${1:-}" = "--include-multi" ]; then
  include_multi=1
  shift
fi

if [ "$#" -eq 0 ]; then
  default_inputs=()
  if [ -e scoring/baseline_outputs.json ]; then
    default_inputs+=(scoring/baseline_outputs.json)
  fi
  if [ -e scoring/ai_noether_merged_outputs.json ]; then
    default_inputs+=(scoring/ai_noether_merged_outputs.json)
  else
    default_inputs+=(scoring/ai_noether_exact_outputs.json)
  fi
  if [ -e scoring/ai_noether_kepler_multi_outputs.json ]; then
    default_inputs+=(scoring/ai_noether_kepler_multi_outputs.json)
    include_multi=1
  fi
  set -- "${default_inputs[@]}"
fi
if [ "$include_multi" -eq 1 ]; then
  python eval/evaluate_exact.py --input "$@" --output scoring/scores.json --include-multi
else
  python eval/evaluate_exact.py --input "$@" --output scoring/scores.json
fi
