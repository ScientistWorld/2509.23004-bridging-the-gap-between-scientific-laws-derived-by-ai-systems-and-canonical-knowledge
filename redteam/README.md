# Benchmark scoring audit

All computations run in a submitted CPU job. Run `bash redteam/run_all.sh` in
the gym container at `/home/user`. Each attempt also has its own `run.sh`.
`run_one.py` temporarily installs output artifacts, invokes visible training
evaluation and then **`bash scripts/evaluate_test.sh` with no arguments**, saves
the resulting JSON and exit code, and restores the scoring directory byte for
byte. Candidate generation and hidden evaluation run in separate processes.
No evaluator file or Python environment is altered.

`generate_reference.py` imports only the improve-mode reference implementation.
`visible_cases.py` and `prepare_shortcut.py` read only public data, with five
shortcuts explicitly reusing method-generated reference outputs to save compute.
Their individual runners regenerate that cache when necessary.
Reference_seed_{11,23,47} rerun every case that can affect the hidden score;
the omitted 64 single-axiom cases cannot affect it. Reference snapshots are used
only in audit analysis, never as inputs to a shortcut.

`honest_broader` runs the actual algorithm on five additional Escape Velocity
cases. Its paired ablation removes only those additional explanations. A separate
check with the visible evaluator records whether the added explanations solve
the promised task, even when the hidden test omits the broad experiment.

`summary.json` reports raw metric values, weighted raw deltas, and a normalized
rank for an explicit audit population. The actual future ranking population is
unknown; use componentwise equality/dominance to make population-independent
claims. Coefficient magnitudes and better directions are honored. No units-based
advantage is assumed.

The report is `REDTEAM.md` at the repository root. Runtime work and verbose logs
are ignored. Each attempt's candidates, train scores, test scores and exit status
are retained; a failed evaluator has a status file and no fabricated score file.
