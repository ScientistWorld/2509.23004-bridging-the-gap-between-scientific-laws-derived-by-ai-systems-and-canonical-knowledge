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
#   ./evaluate.sh                                                   # evaluate default artifacts
#   ./evaluate.sh --include-multi scoring/outputs.json              # include Kepler pair scores
#   ./evaluate.sh --include-triples --include-multi scoring/outputs.json
#
# Called from run.sh after training, or independently.

set -e

cd /home/user

mkdir -p scoring

include_multi=0
include_triples=0
while [ "$#" -gt 0 ]; do
  case "${1:-}" in
    --include-multi)
      include_multi=1
      shift
      ;;
    --include-triples)
      include_triples=1
      shift
      ;;
    *)
      break
      ;;
  esac
done

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
args=(--input "$@" --output scoring/scores.json)
if [ "$include_multi" -eq 1 ]; then
  args+=(--include-multi)
fi
if [ "$include_triples" -eq 1 ]; then
  args+=(--include-triples)
fi
python eval/evaluate_exact.py "${args[@]}"
