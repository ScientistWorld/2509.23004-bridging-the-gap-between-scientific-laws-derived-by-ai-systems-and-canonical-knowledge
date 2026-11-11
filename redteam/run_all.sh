#!/bin/bash
# Submit this script as one CPU job. Each attempt writes its own checkpoint.
set -uo pipefail
cd /home/user
# Restore scripts/run.sh after the submitted shell exits, never from this
# script: overwriting an executing shell script changes its unread commands.
mkdir -p redteam/_state
date -u +%FT%TZ > redteam/_state/job_started.txt
python --version > redteam/runtime.txt
Singular --version >> redteam/runtime.txt 2>&1
python -c 'import sympy; print("SymPy",sympy.__version__)' >> redteam/runtime.txt
for name in \
    reference_seed_11 reference_seed_23 reference_seed_47 \
    honest_stronger honest_weaker honest_broader honest_broader_weaker \
    shortcut_bruteforce_dictionary shortcut_answer_replay \
    shortcut_fabricated_problem shortcut_contradiction shortcut_contradiction_guarded \
    shortcut_target_copy shortcut_forged_flags shortcut_constant_zero \
    shortcut_case_multiplication shortcut_omit_broad shortcut_move_baseline \
    shortcut_empty_output shortcut_empty_shape shortcut_unlisted_method shortcut_invalid_null
do
    echo "AUDIT BEGIN $name $(date -u +%FT%TZ)"
    bash "redteam/$name/run.sh"
    code=$?
    echo "AUDIT END $name exit=$code $(date -u +%FT%TZ)"
done
python redteam/summarize.py
