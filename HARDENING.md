# Hardening report (iterations 12–13, final)

## Summary

* **What `REVIEW.md` asked for is done.** The review found single-axiom recovery
  and explanation at their bound, and the only better variant shown was a sign
  prior (+0.05). This iteration adds a fourth scored experiment,
  **`multiple_consequences`**, set where the paper's method falls short: 59
  held-out instances with **two to five** removed axioms. Four of the held-out
  theories are **larger** (8–10 axioms, 12–16 variables). Each instance comes
  with several observed laws that together determine the removed axioms. The
  reference recovers **0.864**. An honest variant recovers **0.949**: it is
  better on 6 instances and worse on 1, paired on the same instances. Four
  reference draws gave identical results on this experiment. On train the same
  variant goes from 0.857 to 1.000 (+6/−0).
* **Better results score higher.** The rank gain `dW` of five honest variants is
  +0.033 to +0.080 (sparse-law + sign prior: **+0.080**, normalized `dZ`
  +0.21). The reference's own run-to-run spread is −0.0014 to +0.0042 over
  three redraws. The weaker variants and the baselines fall below the reference
  in the expected order (−0.12 to −0.97). Train ranks them the same way.
* **The reference is restored to the paper's Reason step.** The paper tests
  *every* subset of each component's generators; the official code has no cap.
  The earlier reproduction capped this at 400 subsets. That made a one-flag
  change pay: raising the cap scored **+0.055** and recovered 10 more instances
  on the new experiment. The reference now tests up to a fixed count of **4000
  subsets**. This covers every subset of 57 of the 59 instances and recovers the
  remaining 2 anyway. The worst instance takes 7.6 s against the 60 s limit, so
  the result does not depend on machine load. A 5× larger budget (20000) now
  ties (−0.0014). The old 400 setting scores −0.0565.
* **Shortcuts.** Every shortcut probe scores at or near the bottom (−0.28 to
  −1.27), except reading the answers from **git history** (+0.406). The
  evaluator cannot close that one; it is left to the shortcut grader (see
  below). Committed job logs also held three held-out examples; they are now
  redacted and no longer printed.

`dW` means the experiment-weighted, coefficient-weighted improvement over the
reference row. Each metric is taken in its better direction, using the coefficient
magnitudes in `scoring/reference.json`, before population normalization.
`dZ` divides each metric by its population spread over the rows of the same run
that cover all four experiments. That stands in for the unknown future
population, so only its sign and ordering are meaningful. Paired counts
(`+better/−worse`) compare per instance with the reference's outcome on the same
instance. Full rows: `hardening/summary_final.json` (test) and
`hardening/summary_train.json` (train). Before snapshots:
`hardening/summary_job4.json` (new experiment, old reference) and
`hardening/summary.json` (iteration 11). Produced by `hardening/rank.py` and
`hardening/mc_report.py`.

## Starting point

At the end of iteration 11 the gym had three scored experiments (single, two
and three missing axioms; weights 0.40/0.35/0.25). It had a sealed evaluator that
runs every solver on held-out theories, sound/nontrivial/recovered checks in
Singular, and failure = worst value everywhere. `REVIEW.md` then reported that
the hidden test reproduces, and listed one weakness, quoted above.

## What changed

### 1. New experiment: `multiple_consequences` (weight 0.25)

The paper's Section 3.3 shows that observing *several* consequences lets
AI-Noether recover missing axioms *decoupled*, i.e. exactly rather than as a
coupled substitute. It demonstrates this on one theory (relativistic laws,
three removed axioms). The experiment measures that claim across many theories
and beyond the paper's scale:

* **Observed laws.** For each theory and each unmeasured quantity `h`, the
  builder takes the simplest element (at most 30 terms, degree 12) of the
  elimination ideal of the complete theory onto the measured variables plus `h`.
  It is divided by its nonzero monomial factor when that stays in the ideal.
  This is the law an experiment that also measures `h` would observe.
* **Removals of 2–5 axioms.** Each removal comes with the target plus a seeded
  growing set of observed laws, kept only when:
  * the laws and the known axioms imply every removed axiom wherever the nonzero
    quantities are nonzero (*identifiable*, so every instance is solvable);
  * each removed axiom is needed for some chosen law;
  * no removed axiom already follows from the known axioms, the laws and the laws
    with nonzero factors divided out.

  Quotas per theory are 2/3/3/3 removals of 2/3/4/5 axioms.
* **Larger theories.** Four held-out theories exist only in
  `eval/test/systems_mc`: Bohr photoionization, cyclotron orbit, LC oscillator
  and orbital period/energy. Four public train theories in `data/systems_mc_train`
  extend the paper's Kepler, escape-velocity, oscillator and time-dilation
  theories with 2–4 further physical laws.
* **Slices.** Test has 59 instances (28/19/6/6 by number removed, from 15
  theories). Train has 42 (18/18/6). An oracle that submits the removed axioms
  scores 1 on every instance of both slices (smoke check in every job).
* **Scoring.** `recovery_rate` has coefficient 1.0: one set of at most
  `num_missing` polynomials derives every observed law, is sound and nontrivial,
  and implies every removed axiom on the physical locus. `top1_success_rate`
  has 0.3 and the constraint `unsound_rate` 0.3. `explanation_rate` and
  `axiom_recovery_rate` are diagnostics (coefficient 0): on identifiable
  instances they equal recovery. Scoring code is the same as for the other
  experiments, in both evaluators.
* **Design iterations.**
  * v1 allowed removals that the observed laws do not identify. Every honest
    variant was stuck at the same recovery (0.382), so it showed no headroom.
  * v2 made every instance identifiable but had only 43 test instances, all
    from small theories.
  * v3 (final) adds the larger theories and the four- and five-axiom removals.
    This is where the reference falls short.

### 2. Reference restored to the paper's every-subset Reason step

`method/exact_abduction_runner.py` changes `--max-sets` from 400 to 4000. The
paper (Section 2.1) "test[s] whether any subset" of a component's generators
derives the target. The official `generate_candidate_sets` enumerates all of
them without a cap and relies on a 7200 s timeout. The 400 cap was an earlier
iteration's simplification. It binds only on the new experiment (on 20 of its
59 instances); the other three experiments never exceed 132 subsets.
`reference_maxsets_400` keeps the old setting as a hardening row.

### 3. Rank configuration

Experiment weights are **0.30 / 0.25 / 0.20 / 0.25** (single / two / three /
multiple consequences). They were 0.40 / 0.35 / 0.25. Reasons:
* single-axiom recovery is at its bound, so that experiment now mostly measures
  ranking and soundness;
* the new experiment measures one of the paper's central claims (Section 3.3:
  multiple consequences give decoupled recovery);
* the new experiment holds most of the gym's recovery headroom.

Coefficients are unchanged. `scoring/reference.json` results come from the
final hidden-test run; the paper's numbers stay under `_paper_reported`.

### 4. Answer hygiene

* `hardening/mc_report.py` printed three held-out instances with their removed
  axioms into job logs, which the system commits (`jobs/*/stdout.log`,
  `result.json`, checkpoints). It now prints examples only for train, and the
  working-tree copies of those logs are redacted. No tracked file outside
  `eval/test/` now contains a held-out removed axiom (checked by string search
  over `git ls-files`). The lines remain in older commits, like everything else
  in the history.
* The gitignored solver caches of the hidden test (`eval/test/_cache`) held the
  git-history shortcut's outputs, i.e. the answers. They are deleted. They are
  rebuilt only when a run passes `--cache-dir`.
* `scoring/CONSTRAINTS.md` and `scoring/DIRECTION.md` name job logs next to
  repository history as forbidden sources.

### 5. Documentation

`briefing/problem.md`, `briefing/evaluation.md`, `briefing/overview.md`,
`briefing/method.md`, `scoring/EXPERIMENTS.md`, `scoring/TARGETS.md`,
`scoring/DIRECTION.md` and `scoring/CONSTRAINTS.md` describe the four
experiments, the new weights, the data and the reference's budget.

All of this was checked in one final job, `80b1370b-9dd`. It ran:
* the gym's solvers on the hidden test, giving `scoring/scores_test.json`;
* three reference redraws and the 400 and 20000 budgets;
* five better and three weaker variants and the brute-force probe;
* all shortcut probes;
* the gym's solvers and five variants on train;
* `validate.py`, which passed.

## Do better results score higher?

Held-out slice, all four experiments; `dW` versus the reference row of its run.

| Attempt | What it is | Before (iteration 11, 3 exps) | Intermediate (new exp, 400-subset reference) | **After** dW (dZ) | Paired after (+better/−worse) |
|---|---|---:|---:|---:|---|
| `variant_sparse_sign` | sparse-law component + best-first subsets + greedy completion + degenerate-component pruning + sign prior | – | +0.125 | **+0.080** (+0.21) | multi-consequence recovery +6/−1 (0.864 → 0.949); single top-1 +7/−0, unsound +17/−0; two/three unsound +6/−0, +3/−0 |
| `variant_greedy_sign` | best-first + greedy completion + sign prior | – | +0.107 | +0.056 (+0.15) | single top-1 +9/−0, unsound +17/−0; multi-consequence ties |
| `variant_bestfirst_sign` | best-first + sign prior | – | +0.108 | +0.055 (+0.15) | as above, two-axiom unsound +6/−0 |
| `variant_sign_prior` | sign prior only | +0.053 / +0.049 | +0.039 | +0.042 (+0.12) | single top-1 +8/−1, unsound +14/−0 |
| `variant_sparse` | sparse-law component without the sign prior | – | +0.081 | +0.033 (+0.08) | multi-consequence recovery +6/−1 |
| `reference_draw2`, `reference_draw3`, `reference_maxsets_20000` | reference redraws (last one with 5× budget) | ±0.006 (5 draws) | −0.0002, −0.0002 | −0.0000, +0.0042, −0.0014 | top-1 ±2–3 instances; multi-consequence identical |
| `reference_maxsets_400` | earlier reference (400 subsets) | – | 0 (it was the reference) | **−0.057** (−0.13) | multi-consequence −10 |
| `variant_saturation_only` | one saturated component instead of a decomposition | −0.158 | – | −0.116 (−0.27) | single recovery −25 |
| `bruteforce_binomial` | brute force: two-term laws of the saturated ideal | – | −0.309 | −0.361 (−0.92) | multi-consequence +5/−23; single −31 |
| `weaker_unranked_singletons` | no ranking, singletons only, no degeneracy filter | −0.247 | – | −0.489 (−1.20) | unsound −34/−37/−18/−26 |
| `weaker_no_reasoning` | no Reason step | −0.331 | – | −0.519 (−1.24) | single recovery −18; multi-consequence −51 |
| `enumerative_baseline` | syntax-guided enumeration | −0.628 | −0.692 | −0.744 (−1.97) | multi-consequence −51 |
| `no_abduction_baseline` | proposes nothing | −0.929 | −0.917 | −0.969 (−2.52) | — |

The variants' gains shrank from the intermediate to the final column for one
reason: the restored reference now finds the 10 multiple-consequence recoveries
that best-first ordering and greedy completion used to add. These variants
still improve ranking and soundness. Only the sparse-law component adds
recoveries the paper's procedure cannot reach.

**Train agrees** (`hardening/summary_train.json`):

| Attempt | dW |
|---|---:|
| sparse + sign | +0.146 (multi-consequence +6/−0, 0.857 → 1.000) |
| sign prior | +0.040 |
| 400-subset reference | −0.014 |
| brute force | −0.343 |
| no reasoning | −0.505 |
| enumerative baseline | −0.817 |
| empty baseline | −0.914 |

**Noise.** Singular's `minAss` returns different generating sets from run to
run, as in iteration 11. The four final draws (anchor, two redraws, the 20000
run) span 0.0056 in `dW`. On `multiple_consequences` all four are identical
instance by instance. The anchor is the median draw. The best variant's gain
is 14× that span. Its multiple-consequence gain (+6/−1 on test, +6/−0 on train)
does not come from method noise.

**Why the sparse-law variant is a better method, not a fitted rule.**
* It adds one candidate component to the paper's pipeline: two-term laws of
  ⟨known, observed⟩ saturated by the nonzero quantities.
* Physical laws are often monomial relations, and many removed axioms are not
  generators of any prime component.
* The same binomials alone, without the decomposition (`bruteforce_binomial`),
  recover only 0.559. That is far below the reference.
* Its remaining misses (3 of 59) are four- and five-axiom removals with
  non-binomial axioms. That is headroom for a better method.

## Shortcuts

Final dW on the hidden test, all four experiments.

| Shortcut | Before (iteration 11 evaluator) | Fix | After |
|---|---:|---|---:|
| Raise the reference's own subset budget (`reference_maxsets_4000` then, `reference_maxsets_20000` now) | **+0.055** (intermediate) | reference restored to the paper's every-subset procedure (fix 2) | −0.0014 (ties) |
| Answers from git history (`oracle_git_lookup`) | +0.451 | not closable by the evaluator | **+0.406** (left) |
| Answers from committed job logs (3 held-out instances) | not run (bounded by 3 of 218 instances) | log lines redacted; printer fixed | closed in the working tree |
| Hand back the observed laws as the missing axioms (`observed_laws`, new experiment) | – | nontriviality against ⟨known, observed laws, stripped laws⟩ | −1.12 on the experiment (−0.28 weighted) |
| Read the hidden instance file during the run | −1.229 | private files off disk (iteration 11) | −1.269 |
| Search the workspace for answer files | −0.929 | same | −0.969 |
| Contradiction `[1, hidden variable]` | −1.229 | soundness test | −1.269 |
| Copy the target / known axioms; stripped target | −0.929 | nontriviality test | −0.969 |
| Fabricated problem, forged flags / score file, constant zero | −0.929 | evaluator owns instances, ignores solver fields | −0.969 |
| Oversized sets | −0.931 | at most `num_missing` polynomials per set | −0.977 |
| Crash, `{}`, `null` sets | −1.229 | failure = worst value in every metric of every experiment | −1.269 |

All probes were rerun in the final job against the final instances, evaluator
and reference.

### Shortcuts left, and why

* **Answers from repository history** (+0.406, measured with
  `git show HEAD:eval/test/instances.json`). The held-out theories are
  committed. A solver runs in the same checkout, so the evaluator cannot stop it
  from reading `.git`. Moving or hiding `.git` during a run would risk losing
  the repository if the job is killed. It is an unambiguous cheat that
  `scoring/CONSTRAINTS.md` forbids, it is easy to see in solver code, and it
  pays only if the hidden test's checkout carries the history. It is left to the
  shortcut grader. The same holds for the held-out example lines in older
  commits of `jobs/` logs.
* **Process-level interference** (killing the evaluator after writing a score
  file, a background process copying the temporary scoring scripts). There are
  no defenses against leftover processes, as instructed; such attacks are
  visible in solver code.
* **More search.** It is a legitimate lever and no longer pays on its own: the
  5× budget ties.

## Reference before and after

| Slice | Experiment | Iteration 11 (before): recovery / explanation / top-1 / unsound | Intermediate (400 subsets) | **Final** |
|---|---|---|---|---|
| test | single (64) | 1.000 / 1.000 / 0.844 / 0.344 | 1.000 / 1.000 / 0.844 / 0.344 | 1.000 / 1.000 / 0.828 / 0.344 |
| test | two missing (55) | 0 / 0.655 / 0.600 / 0.145 | 0 / 0.655 / 0.600 / 0.164 | 0 / 0.655 / 0.600 / 0.145 |
| test | three missing (40) | 0 / 0.300 / 0.275 / 0.050 | 0 / 0.300 / 0.300 / 0.050 | 0 / 0.300 / 0.275 / 0.075 |
| test | multiple consequences (59) | – | 0.695 / 0.695 / 0.695 / 0 | **0.864 / 0.864 / 0.864 / 0** |
| train | single (58) | 1.000 / 1.000 / 0.845 / 0.466 | – | 1.000 / 1.000 / 0.845 / 0.466 |
| train | two missing (34) | 0.088 / 0.500 / 0.353 / 0.206 | – | 0.088 / 0.500 / 0.353 / 0.206 |
| train | three missing (33) | 0 / 0.394 / 0.303 / 0.061 | – | 0 / 0.394 / 0.303 / 0.091 |
| train | multiple consequences (42) | – | 0.809 / 0.809 / 0.786 / 0 (400-subset row of the final job) | 0.857 / 0.857 / 0.833 / 0 |

* The first three experiments differ only within the draw noise above. The
  budget change does not reach them.
* By number of removed axioms, the final reference recovers 27/28, 16/19, 4/6
  and 4/6 of the multiple-consequence test instances.
* The reference and both baselines were rerun from the final code on both
  slices: `scoring/scores_test.json`, `scoring/scores_train.json` and
  `scoring/scores.json` come from that run. `scripts/run.sh` reproduces it end
  to end.
* The paper's direction holds on both slices:
  * single removals are recovered (paper 73/75);
  * about half of two-axiom and a third of three-axiom removals are explained
    (paper 49% and 28%);
  * several observed laws turn coupled explanations into exact recovery of
    the removed axioms (paper Section 3.3);
  * the empty and enumerative baselines score far below (paper: its LLM and
    cvc5 baselines solve none).

## Headroom check

**Scored metrics where the reference sits at the bound:**
* single-axiom `recovery_rate` = 1.0 and `explanation_rate` = 1.0;
* multiple-consequence `unsound_rate` = 0.

**Below the bound, with a demonstrated better method:**
* multiple-consequence `recovery_rate` and `top1_success_rate`: 0.864 → 0.949
  (sparse-law variant);
* single-axiom top-1: 0.828 → 0.969, and unsound: 0.344 → 0.078 (greedy/sign
  variants);
* two- and three-axiom top-1 and unsound (e.g. unsound 0.145 → 0.018 and
  0.075 → 0).

**Below the bound, no improvement shown:**
* two- and three-axiom `explanation_rate` (0.655 / 0.300). None of the variants
  tried raises it: extra orders, saturation, dimension ranking, canonical
  generators, best-first, greedy completion, sparse laws.

What was added for headroom: the `multiple_consequences` experiment (fix 1).
Every instance is solvable (the oracle scores 1). No simple variant reaches the
bound there.

**Brute force.** The binomial brute force recovers 0.559 against 0.864 on the
new experiment and ranks −0.36 overall. The enumerative baseline recovers none.
Enumerating every subset is now the reference itself (the paper's procedure);
a 5× larger budget ties.

**Baselines.** Both baselines are clearly below the reference on every
experiment, with room above the reference.

## What I could not fix

* The git-history answer leak (above).
* Reference nondeterminism. It is inherent to Singular's `minAss` and the
  official code. It is small (±0.005) and absent on the new experiment.
* Two- and three-axiom explanation headroom is not demonstrated.
* Decoupled recovery in the single-target two- and three-axiom experiments stays
  unscored: it is out of reach for every honest method there. The new
  experiment scores decoupled recovery where the observed laws make it possible.
* Inherited scope limits, unchanged:
  * The paper's noisy pathway (numerical decomposition, symbolic regression,
    KeYmaera X) is not reproduced.
  * Its cvc5 and GPT-5 Pro baselines are not reproduced.
  * Train keeps only the well-posed removals of the paper's systems.
  * The per-instance limit is 60 s instead of 7200 s. The reference needs at
    most about 8 s.

## Reproducing

* `bash scripts/run.sh`:
  * rebuilds missing instances;
  * runs the oracle smoke check;
  * evaluates the gym's solvers on the hidden test and train;
  * runs the hardening rows and shortcut probes;
  * writes the rank summaries and validates.
* `bash scripts/evaluate_test.sh` (no arguments) is the hidden test.
* A probe set alone: `python eval/test/evaluate.py --solvers-dir
  hardening/solvers_<set> --output hardening/<file>.json --details-out
  eval/test/_runs/<file>_details.json`, then `python hardening/rank.py
  hardening/<file>.json:eval/test/_runs/<file>_details.json`.
