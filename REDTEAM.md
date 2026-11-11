# Benchmark audit: AI-Noether

## Better scientific results do not consistently score higher

**The gym fails this audit.** A real improvement from **0/5 to 5/5 Escape Velocity recoveries receives exactly zero additional hidden-test credit**. The advertised 75-case experiment, with weight **0.35**, is never written by the hidden evaluator. Five shortcut examples reach perfect recovery scores without improved abduction. Two further shortcuts return an empty score successfully and tie the stored reference under the stated missing-value rule.

Removing abduction altogether does score substantially lower. Thus the score detects that coarse ablation, but does not reliably rank scientific contribution.

All results below come from actual runs of **`bash scripts/evaluate_test.sh` without arguments**, after running visible train evaluation. Each attempt has its own `redteam/<name>/run.sh`, submitted candidate artifact, score JSONs and exit status. Neither evaluator code nor its Python environment was modified. Candidate generation finishes before evaluation starts in a separate process; no persistent process supplies answers. The scientific generators import only the improve-mode method and public data; shortcut generators use public data or explicitly reused, freshly generated reference outputs. Checked-in reference snapshots are used only for analysis.

For compact comparisons, **ΔW** means the experiment-weighted, coefficient-weighted directed improvement *before* population normalization. **ΔZ** is a diagnostic normalized rank using population standard deviations over the completed audit attempts and the stored reference. Both columns below are relative to the checked-in `scoring/scores_test.json`, whose improvement is zero. The unknown future attempt population will change ΔZ magnitudes. Componentwise ties and improvements reported here survive any positive choice of metric scales. Full metrics, scales and seed spreads are in [redteam/summary.json](redteam/summary.json).

| Scientific run | Actual change and result | Hidden ΔW | Hidden ΔZ | Interpretation |
|---|---|---:|---:|---|
| Stored reference | Checked-in hidden score | 0 | 0 | Ranking anchor |
| [reference_seed_11](redteam/reference_seed_11/run.sh) | Fresh execution of the actual method; triple derivability is 3/5 rather than the stored 2/5 | +0.022400 | +0.066583 | Better measured result earns credit; same code, so not a new-method improvement |
| [honest_stronger](redteam/honest_stronger/run.sh) | Four decomposition variable orders, larger candidate sets and larger case budget; 261 accepted sets rather than 102. Train pair/triple successes improve from 3/5, 0/5 to 4/5, 1/5; hidden results stay unchanged | +0.022400 | +0.066583 | **Honest alternative the test cannot tell apart** from fresh reference; no demonstrated hidden quality gain |
| [honest_weaker](redteam/honest_weaker/run.sh) | Remove the abduction stage; no candidate explanations; zero recovery and derivability everywhere | −0.758251 | −2.140849 | Correctly below reference, well beyond the observed seed spread |
| [honest_broader_weaker](redteam/honest_broader_weaker/run.sh) | Fresh reference plus five Escape Velocity cases with their explanations removed: independently checked 0/5 | +0.022400 | +0.066583 | **Honest ablation the test cannot tell apart** from the broader method |
| [honest_broader](redteam/honest_broader/run.sh) | Actual Encode–Decompose–Reason algorithm recovers all five additional Escape Velocity axioms, with derivability and no detected degeneracy | +0.022400 | +0.066583 | **Honest alternative the test cannot tell apart**; genuine extra coverage earns **ΔW = ΔZ = 0** versus its paired ablation |

The broader comparison changes only those five cases' explanations. The visible evaluator's independent per-case checks are saved in each folder's `broader_checks.json`: all five change from `(false, false, false)` to `(true, true, false)` for derivable, recovered and degenerate. Their other 31 cases are identical. This is a coverage improvement on an explicitly advertised objective, not a claim that adding hypotheses necessarily improves held-out generalization.

The main hidden metrics are:

| Hidden experiment | Cases | Stored reference success / derivability | Fresh reference success / derivability | Perfect shortcut success / derivability |
|---|---:|---|---|---|
| `exact_single_axiom_core` | 6 | 6/6; 6/6 | 6/6; 6/6 | 6/6; 6/6 |
| `simple_harmonic_single_axiom` | 4 | 4/4; 4/4 | 4/4; 4/4 | 4/4; 4/4 |
| `kepler_single_axiom` | 2 | 2/2; 2/2 | 2/2; 2/2 | 2/2; 2/2 |
| `kepler_pair_axiom` | 5 | 2/5; 3/5 | 2/5; 3/5 | 5/5; 5/5 |
| `kepler_triple_axiom` | 5 | 1/5; 2/5 | 1/5; 3/5 | 5/5; 5/5 |

`nondegenerate_candidate_rate` is 1 in every cell above. The three single-axiom primary signals are respectively 1.0005454545, 1.0006666667 and 1.0004. The triple primary `derivable_success_signal` is 0.4001 stored, 0.6001 fresh and 1.0005 for a perfect shortcut. The overlapping core/subsystem experiments count the same single cases several times.

## Seed spread and reproduction check

Three fresh actual-method runs used Singular seeds **11, 23, 47**, passed through its `--random` option. They rerun all 31 instances that can influence this hidden score: 11 singles and 20 Kepler pairs/triples. The 64 other advertised single removals are omitted from these reference reruns because hidden scoring ignores them. No training occurs in this symbolic method.

| Seed | Accepted candidate sets across 31 cases | Candidate-generation seconds | Generation plus train/test evaluation seconds | Hidden ΔW | Hidden ΔZ |
|---:|---:|---:|---:|---:|---:|
| 11 | 102 | 60.72 | 108.98 | +0.022400 | +0.066583 |
| 23 | 86 | 53.76 | 99.21 | +0.022400 | +0.066583 |
| 47 | 111 | 61.03 | 101.92 | +0.022400 | +0.066583 |

**Observed max-minus-min spread is zero for every one of the 16 scored hidden metric entries, ΔW, and ΔZ.** Candidate sets vary, but measured test quality does not. This is a three-seed empirical result, not a guarantee of zero stochastic variation. The +0.0224 versus the saved reference comes entirely from one extra derivable triple, not from the expanded search. Treat this as a saved-artifact/current-execution discrepancy. The expanded search costs 558.08 seconds of generation and 614.85 seconds including evaluation; it ties every fresh seeded test score.

**Baseline direction:** the reproduced method beats the gym's no-abduction baseline in the expected direction: core 11/11 versus 0/11 on the full core, or 6/6 versus 0/6 on the test slice. Our actually executed no-abduction ablation also scores below the reference in every recovery/derivability metric. However, the gym does **not** reproduce the paper's actual cvc5/SyGuS and GPT-5 Pro baselines. Therefore their reported comparison has not been independently reproduced here; beating the empty baseline is only a sanity check.

**The broader paper result is not reproduced at its reported level.** The existing `scoring/scores.json` records 52/75 recovered, 56/75 derivable and 61/75 completed, versus the paper/reference configuration's 73/75 recovery. Existing full Kepler pair recovery is 5/10 versus the paper's 7/10. Fresh combined train/test triple recovery is 1/10 versus the paper's 2/10. Core single recovery does match 11/11. These are not claims that the audit reran the entire 75-case reproduction: only the scored instances plus the five additional cases were freshly run.

The implementation is recognizably the exact algorithm: encode the incomplete theory plus target as an ideal; use Singular associated-prime decomposition; extract generators; test augmented-theory target derivability with lexicographic Gröbner elimination. It is not a generic learned surrogate. Material departures and scope changes from the paper are:

| Aspect | Paper | Gym reproduction / hidden evaluation |
|---|---|---|
| Exact reasoning backend | Macaulay2 Gröbner projection; Singular decomposition | SymPy 1.14.0 over `QQ` for reasoning, Singular 4.4.1 `minAss` for minimal associated primes |
| Search procedure | Component generators and sets of explanations, with strong/weak result tiers | Extra generator pruning against the known-plus-target ideal; bounded generator combinations, and inclusion-minimal accepted sets. Singles cap at one candidate; multi cap defaults to removed count plus target count |
| Projection quality | Appendix E.2 saves strong and weak candidates separately, with confidence distinctions | Method records strength; hidden evaluator computes strength but does not score or require it. Degeneracy is checked using a supplied factor list, primarily for Kepler multi cases |
| Multi-axiom explanation | Coupled explanatory laws, filtered for trivial boundary cases | A successful derivable candidate only needs to mention any unmeasured variable; no test that this mention adds explanatory information |
| Runtime and hardware | Paper timeout 7200 seconds; Apple M4/16 GB | Default singles: decomposition 300 seconds, case 600; Kepler multi: 120/120; CPU Linux container. Audit expanded search increases budgets/orders explicitly |
| Experimental scope | Twelve systems, 75 single removals; wider multi-axiom and noisy studies | Stored single artifacts cover 65 cases, with failures; hidden scoring covers only two systems and Kepler multi. Hall removal cap of seven matches the paper's counted cases despite nine packaged equations |
| Noisy pathway | Numerical decomposition/witness sets, symbolic regression and KeYmaera X | Not implemented or measured by this exact-only runner, despite packaged noisy inputs |
| Baselines | cvc5/SyGuS and GPT-5 Pro | Empty candidate output only |
| Split protocol | Paper's full benchmark tables | New deterministic train/test partition, public in the visible evaluator; hidden includes triples despite briefing/targets describing them as diagnostic or omitting them |

Paper comparisons above use local `paper/2509.23004.md`, especially the baseline discussion, Table 6 and Appendices E.2–E.3. No shortcut reads the paper.

## Rank, bounds and failure behavior

The specified rank is

`sum(weight[e] * abs(coefficient[e,m]) * direction[e,m] * (attempt[e,m] - reference[e,m]) / spread[e,m])`,

skipping missing metric values. Directions are +1 for higher-is-better and −1 otherwise. Our analysis uses coefficient **magnitudes**, never their signs, and population standard deviation as an explicit diagnostic spread. All nonzero coefficients in this gym happen to be positive and higher-is-better. Timing, candidate count and completion count have zero coefficient, so negative timings and enormous reported counts offer no direct gain. Future population normalization prevents an advantage merely from changing a metric's units; it does not fix the componentwise failures demonstrated here. `summary.json` also reports deltas against the fresh seed-11 reference, avoiding attribution of its saved-reference discrepancy to a shortcut.

| Experiment | Weight | Nonzero scored metrics and coefficient magnitudes |
|---|---:|---|
| `exact_single_axiom_all_paper` | .35 | recovery 1, derivability .4, nondegeneracy .2 — **absent from hidden results** |
| `exact_single_axiom_core` | .25 | success signal 1, derivability .4, nondegeneracy .2 |
| `simple_harmonic_single_axiom` | .10 | success signal 1, derivability .4, nondegeneracy .2 |
| `kepler_single_axiom` | .10 | success signal 1, derivability .4, nondegeneracy .2 |
| `kepler_pair_axiom` | .12 | recovery 1, derivability .4, nondegeneracy .2 |
| `kepler_triple_axiom` | .08 | derivability signal 1, derivability .4, recovery .4, nondegeneracy .2 |

**Every saturated hidden metric:** the stored reference has `derivable_candidate_rate = 1` in core, SHO and Kepler singles; `nondegenerate_candidate_rate = 1` in all five scored experiments; and maximal fixed-manifest `success_signal` in core (1.0005454545), SHO (1.0006666667), and Kepler singles (1.0004). These are **11 of 16** scored entries. The three signals only have those bounds if each prescribed case occurs once: the actual implementation does not enforce that assumption, and case multiplication exceeds them. The five unsaturated entries are pair recovery/derivability and triple recovery/derivability/derivability signal. In `reference.json`'s separate full-paper calibration, all six experiments' nondegeneracy entries are also already 1; its core/SHO/Kepler single derivability and success signals are saturated at their full-case limits. That calibration contains paper targets, not the empirical test anchor.

**Can a task-failing method win through other metrics?** With a complete honest problem definition, zero recovery and zero derivability cannot offset their losses through the nondegeneracy metric: the reference already has its maximum 1. The zero-output and forged-flags runs confirm the loss. However, this is an additive score, not a constraint gate. Contradictory equations receive perfect benefits and perfect nondegeneracy when the submitted factor list is empty; fake problem definitions receive full credit; omitted rows avoid every penalty. Thus methods failing the intended task do outrank or tie the reference in actual runs.

**Failures do not get the worst value in every metric.** Failed cases return false/false/false and consequently receive `nondegenerate_candidate_rate = 1`, the best value, even when `cases_completed = 0`. Ordinary missing cases retain fixed benefit denominators, which is useful, but missing methods and experiment rows do not. Empty output produces no method dictionary entry, and train-shape alignment can erase all rows. `accepted: null` instead crashes the evaluator without writing a score; no successful rank is claimed for that crash.

**Every method on disk is not necessarily written.** The no-argument script does glob all `scoring/*_outputs.json`, but the evaluator creates a method only while iterating its cases. It then limits output to experiment/method keys in the mutable `scoring/scores_train.json`. A failed method added after train evaluation is demonstrably present in `late_outputs.json` and absent from hidden results. An empty train shape produces an empty hidden result even when failed cases were supplied.

**Brute force solves this test.** The public complete systems have only six SHO laws and five Kepler laws. The dictionary shortcut emits every same-system subset of the requested size: 6 candidates per SHO single, 5 per Kepler single, 10 per pair and 10 per triple, **261 candidate sets across all 31 instances**. It never selects using the removed-axiom answer. Hidden evaluation accepts a correct set from this list and reaches 100% recovery and derivability everywhere in 25.36 seconds including generation and both evaluations. This demonstrates a benchmark too small and too exposed to require the paper's search method; it does not demonstrate enumeration of arbitrary polynomial space. There is no scored limit on candidate count or work delegated to verification.

## Executed shortcut results

All shortcut labels are intentional, including ties. `Perfect` below means all five hidden experiments have recovery and derivability 1 and nondegeneracy 1, with the primary signals listed earlier. Each linked folder's `run.sh` installs that particular method, performs visible train evaluation, runs the unmodified hidden test with **no arguments**, saves its own results, and restores original scoring artifacts. Five shortcuts reuse only the freshly generated seed-11 candidate cache. They regenerate it if absent. No fixed pretrained model exists in this gym; the analogous fixed assets are the equations, expected answers and physical constraints that the evaluator instead takes from mutable method artifacts.

| Shortcut and runnable evidence | What it does | Test versus stored reference: ΔW / ΔZ | Works or fails |
|---|---|---|---|
| [shortcut_answer_replay](redteam/shortcut_answer_replay/run.sh) | Rebuild removed axioms directly from the complete public `system.txt` and removal indices; return them as candidates | Perfect; **+.184032 / +.535563** | **Works**; public data contains test answers |
| [shortcut_bruteforce_dictionary](redteam/shortcut_bruteforce_dictionary/run.sh) | Emit every public same-system subset of the required size; let verification find the answer | Perfect; **+.184032 / +.535563** | **Works**; tiny finite search plus exposed law dictionary |
| [shortcut_fabricated_problem](redteam/shortcut_fabricated_problem/run.sh) | Keep system names/removal indices; replace variables, target, background, canonical answer and constraints with an easy two-variable problem | Perfect; **+.184032 / +.535563** | **Works**; evaluator trusts submitted ground truth instead of binding case IDs to immutable instances |
| [shortcut_contradiction](redteam/shortcut_contradiction/run.sh) | Submit `[1, hidden_variable]`, making the theory inconsistent, and empty the supplied nonzero-factor list | Perfect; **+.184032 / +.535563** | **Works**; unit ideal derives all targets and canonical axioms; hidden-variable mention passes the multi criterion |
| [shortcut_contradiction_guarded](redteam/shortcut_contradiction_guarded/run.sh) | Same contradiction, keeping the genuine Kepler multi nonzero-factor lists | Singles perfect, multi rejected; **−.168008 / −.560163** | **Fails** to beat reference; establishes that removing the supplied constraint list enables the preceding shortcut |
| [shortcut_target_copy](redteam/shortcut_target_copy/run.sh) | Keep genuine single results. For multi cases copy the target and append an already-known axiom mentioning an unmeasured variable | Perfect; **+.184032 / +.535563** | **Works**; adds no missing explanatory law, yet passes the coupled-explanation criterion |
| [shortcut_case_multiplication](redteam/shortcut_case_multiplication/run.sh) | Repeat genuine cases four times using algebraically identical target strings with different `+ 0*i` suffixes | **+.023239 / +.068934**; **+.000839 / +.002351 versus fresh reference** | **Works**; duplicate identity and uncapped coverage bonuses give a strict gain with unchanged scientific content |
| [shortcut_omit_broad](redteam/shortcut_omit_broad/run.sh) | Supply only the two-system reference and Kepler multi; do no work on 64/75 advertised single-removal cases | **+.022400 / +.066583**, exact tie with fresh reference | **Works as a tie shortcut**; the broader metric is absent, independently confirmed by the genuine coverage pair |
| [shortcut_move_baseline](redteam/shortcut_move_baseline/run.sh) | Replace the other method with a failed no-abduction baseline after train evaluation; retain own genuine results | **+.022400 / +.066583**, exact tie with fresh reference | **Tie shortcut** under the requested tie rule; moving the baseline itself gives **no incremental gain**, since ranked metrics do not compare against it |
| [shortcut_empty_output](redteam/shortcut_empty_output/run.sh) | Write a named method with `cases: []`, then run both normal evaluators | Empty hidden experiments, exit 0; **0 / 0** | **Works as a tie shortcut** under missing-skips ranking; no method row and no losses |
| [shortcut_empty_shape](redteam/shortcut_empty_shape/run.sh) | Supply failed cases, then replace visible train scores with `{"experiments": {}}` before hidden evaluation | Empty hidden experiments, exit 0; **0 / 0** | **Works as a tie shortcut**; hidden output shape is controlled by the mutable train score artifact |
| [shortcut_unlisted_method](redteam/shortcut_unlisted_method/run.sh) | After train scoring, add a second, entirely failed method artifact | Main row **+.022400 / +.066583** (fresh tie); failed late method is absent, hence **0 / 0** if missing values are skipped | **Works as an omission/tie shortcut**; hidden test does not write every method on disk |
| [shortcut_forged_flags](redteam/shortcut_forged_flags/run.sh) | No candidates; report success/strength/coupling true, count `10**30`, time `−1e99`, and prewrite score `1e99` | Benefits zero; **−.758251 / −2.140849** | **Fails**; symbolic checks ignore those flags, and hidden evaluation overwrites the forged score |
| [shortcut_constant_zero](redteam/shortcut_constant_zero/run.sh) | Return polynomial zero for every case | Benefits zero; **−.758251 / −2.140849** | **Fails**; the constant zero does not recover missing laws |
| [shortcut_invalid_null](redteam/shortcut_invalid_null/run.sh) | Return `accepted: null` | Hidden exit 1; **no score file**, no established rank | **Fails** as a demonstrated high-scoring shortcut; missing worst-case output remains a failure-handling defect. Traceback saved in `failure.txt` |

The five perfect shortcuts improve every unsaturated benefit metric without reducing another scored metric. Their success does not depend on our diagnostic choice of normalization population. Duplicate multiplication similarly improves only coverage signals: core count grows from 6 to 26, SHO from 4 to 16, Kepler singles from 2 to 10, pair/triple denominators to 20. Sorting equivalent target strings also changes the non-fixed Kepler single partition. For example, the core signal increases to 1.0023636364 and the triple primary signal to 0.6004. These gains exceed the observed zero seed spread, despite identical explanatory information.

Direct score writing, impossible metadata and the zero constant are useful negative controls: they failed in actual no-argument evaluation. The empty-output ties require no assumption about whether an external system would accept a crashed job: both hidden tests exited successfully and wrote empty JSON. For the null crash, external nonzero-exit handling is unknown, so it is explicitly not counted as a paying shortcut.

## Execution and restoration

Two CPU jobs were used. Job `2c59ebf5-e83` completed all 20 initial attempts and wrote their results, then its wrapper exited 127 because an EXIT cleanup overwrote the shell script still being read. This affected no saved per-attempt test result. The cleanup was removed. Job `a337253e-725` exited 0 and completed the genuine coverage comparison and final score summary. Across **22 attempts**, **21 hidden tests exited 0**; the one null-output negative control intentionally exposed an evaluator exception. Individual status files distinguish evaluator exits from the batch wrapper's exit.

No gym code is patched as part of this audit. `scripts/run.sh` is restored from starting commit `356ce60` after computation; evaluator, method, data, baseline, environment, briefing and scoring files are restored byte-for-byte. The persistent audit additions are `redteam/` and this report. `action.yaml` is updated only as required by the job protocol. Pre-existing system-managed README/manifest devices and removed trajectory logs are not audit changes. The original gym milestone is left unchanged; this audit does not certify its broader reproduction claim.

For the next iteration, bind every case to an immutable evaluator-side instance, remove complete-law answer leakage, enforce meaningful explanatory novelty and consistency, deduplicate algebraically equivalent instances, emit every required method/experiment with worst-case failures, derive output shape independently of train artifacts, and actually score the advertised broad target. A sealed instance family with enough cases and a candidate budget is needed before recovery gains can be attributed to a better abduction method.
