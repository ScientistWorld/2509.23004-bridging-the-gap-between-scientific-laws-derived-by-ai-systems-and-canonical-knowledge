#!/bin/bash
# Evaluate the visible train slice of method output artifacts.
#
# Contract mirrors scripts/evaluate.sh: pass explicit output JSON artifacts as
# positional arguments, or omit them to evaluate every scoring/*_outputs.json
# artifact found on disk. Writes scoring/scores_train.json.

set -e

cd /home/user

mkdir -p scoring

include_multi=1
include_triples=1
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
  shopt -s nullglob
  default_inputs=(scoring/*_outputs.json)
  shopt -u nullglob
  if [ "${#default_inputs[@]}" -eq 0 ]; then
    echo "No scoring/*_outputs.json artifacts found to evaluate." >&2
    exit 1
  fi
  set -- "${default_inputs[@]}"
fi

for input_path in "$@"; do
  if [[ "$input_path" == *multi_outputs.json ]]; then
    include_multi=1
  fi
done

args=(--input "$@" --output scoring/scores_train.json)
if [ "$include_multi" -eq 1 ]; then
  args+=(--include-multi)
fi
if [ "$include_triples" -eq 1 ]; then
  args+=(--include-triples)
fi
python eval/train/evaluate.py "${args[@]}"
