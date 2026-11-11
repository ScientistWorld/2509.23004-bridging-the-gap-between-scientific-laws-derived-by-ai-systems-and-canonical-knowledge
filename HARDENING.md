# Hardening report (iteration 11)

## Summary

* **Better results now score higher.** An honest refinement of the reference (a
  physical sign prior on its candidates) scores **+0.049 / +0.053** weighted
  (`dW`, two independent runs). Per instance on the held-out slice it is better
  in 30 comparisons and worse in 2 (draw a), and +29/−3 in draw b. The
  reference's own run-to-run noise is about ±0.005 (five draws span 0.0076), and
  its redraws differ from the anchor by at most 3 instances on any metric. Weaker variants and the baselines score below
  the reference in the expected order.
* **The main measurement bug is fixed.** The evaluator called proposed laws
  "unsound" when they failed on *degenerate* solutions of the complete theory
  (for example at orbit radius r = 0). That flagged true physics as false, such
  as the virial relations U = 2E and E = −K, and inflated the reference's unsound
  rate to 0.65. Soundness is now judged wherever the physically nonzero
  quantities are nonzero, the same convention the recovery test already used.
  The shortcut this would have opened (proposing the target with its nonzero
  monomial factor divided out) is closed by the matching nontriviality test.
* **The large shortcut of the previous design is closed.** A solver reading the
  hidden instance file scored +1.08. It now finds no file and scores at the
  bottom (−1.23).
* **What is left:** a solver that reads the answers from **git history** still
  scores +0.45. The evaluator cannot remove repository history; the separate
  shortcut grader has to catch this.

`dW` throughout means the experiment-weighted, coefficient-weighted improvement
over the reference row, in each metric's better direction, before the
population normalization. Each value uses the coefficients of the evaluator it
was measured with. Full rows, normalized `dZ` and per-instance paired counts are
in `hardening/summary.json` (after) and `hardening/summary_before.json`
(before). The scripts that produced them are `hardening/summarize.py`,
`hardening/smoke_check.py`, `hardening/check_instances.py` and the solver
wrappers under `hardening/solvers_*`.

## Starting point

`REDTEAM.md` audited the original gym, which scored saved outputs on the paper's
public systems. In that gym answer replay, a brute-force dictionary, fabricated
problems, contradictions and target copies all scored perfectly (+0.184 `dW`).
Case multiplication gained, and empty or omitted outputs tied the reference.

Earlier in this iteration a first hardening pass replaced that design (commit
`78d2870`):
* Solvers are scripts (`scripts/solvers/<name>.sh`) that the evaluator runs
  itself on every instance, under a 60 s limit, with at most five ranked
  candidate sets per instance.
* The held-out test uses 14 theories that exist only in `eval/test/systems`,
  anonymized and unit-rescaled. Train uses the paper's 12 public theories.
* Every verdict is recomputed in Singular from the candidate polynomials. A
  failed run gets the worst value in every metric.

That pass verified its design in job `2dc2527b-c11` but left these problems,
which this report addresses:

1. **Soundness test too strict.** It required radical membership in the
   *unsaturated* complete theory, so laws true wherever quantities are nonzero
   were flagged unsound. Of 68 single-axiom instances, 44 had such flags. The
   reference's single-axiom unsound rate was 0.647; on train it was 0.847.
2. **Hidden file readable while solvers run.** Reading
   `eval/test/instances.json` scored +1.079.
3. **`scoring/reference.json` results all zero.**
4. **Multi-axiom `recovery_rate` stuck at 0** for every honest method on test,
   yet carrying coefficient 0.5.
5. **Singular resolved through `PATH`** at every call, so a solver could plant
   its own binary.
6. **Enumerative baseline bounded by wall-clock time**, so its score depended on
   machine speed.

## Fixes (applied together, checked in jobs `cb730765-3f1` and `88527c3d-470`)

**1. Soundness modulo nonzero quantities** (`eval/test/evaluate.py`,
`eval/train/evaluate.py`). A proposed polynomial u is sound iff
u·∏(nonzero quantities) lies in the radical of the complete theory. Equivalently,
u lies in the radical of the complete theory saturated by that product. The
builder precomputes a Gröbner basis of the saturated theory into the hidden part
of each instance (`full_saturated`). Contradictions, laws that force a nonzero
quantity to zero, and stronger-than-true laws remain unsound.

**2. Nontriviality against stripped targets.** A polynomial is now trivial if it
lies in ⟨known axioms, targets, targets with their monomial factor in nonzero
quantities divided out⟩. Without this, fix 1 would let the stripped target
(e.g. elastic collision `m2·v2·(…)` → `(…)`) count as a free explanation.

**3. Well-posedness of instances** (both builders). Two new requirements:
* Some target must not follow from the remaining axioms, not even once
  quantities are assumed nonzero (target ∉ known : nonzero^∞).
* No removed axiom may lie in ⟨known, targets, stripped targets⟩.

Effect: the test slice goes from 166 to 159 instances (64 single / 55 two-axiom /
40 three-axiom). Dropped: 3 elastic-collision singles whose removed axiom
restates the stripped target, 1 Carnot-engine single whose target already
follows generically, and 5 multi-axiom draws; the builder picked 2 new pairs to
refill the quota. Train goes from 126 to 125. Public payloads of all kept
instances are byte-identical, so cached solver outputs stayed valid (checked by
`hardening/check_instances.py prune`). An oracle that submits the removed axioms
now scores recovery = explanation = top-1 = 1 and unsound = 0 on **all 284**
instances (`hardening/smoke_check.py`).

**4. Evaluator-private files off disk while solvers run** (test evaluator,
`PrivateFilesOffDisk`). `instances.json` and `systems/` are held in memory,
deleted for the duration of the solver runs, and written back exactly. Anything
a solver planted there is replaced; restoration also runs on errors and SIGTERM.
If the checkout is read-only, the evaluator continues with a warning.

**5. Singular binary pinned** to an absolute path outside the workspace before
any solver runs.

**6. Deterministic enumerative baseline.** It tests the first 6000 grammar
candidates per instance; 50 s is only a safety stop.

**7. Rank configuration** (`scoring/reference.json`):
* Multi-axiom `recovery_rate` goes from coefficient 0.5 to 0 (diagnostic). It
  was 0 for the reference, every variant and both baselines on test; only
  answer-reading shortcuts moved it. With population normalization, a stuck
  metric would turn a single lucky instance into a large rank gain.
* Results are filled from `scoring/scores_test.json`.
* Experiment weights are unchanged (0.40 / 0.35 / 0.25). They follow the
  paper's emphasis on single-axiom recovery (97%) and multi-axiom recovery (49%).

**8. Documentation.** `briefing/evaluation.md`, `briefing/problem.md`,
`briefing/overview.md`, `briefing/method.md`, `scoring/EXPERIMENTS.md` and
`scoring/TARGETS.md` now describe the corrected definitions and the diagnostic
status of multi-axiom recovery.

## Do better results score higher?

Held-out slice; `dW` versus the reference row.

| Attempt | What it is | dW before (old evaluator) | dW after | Paired after: primary / top-1 / unsound, single · two · three (+better/−worse) |
|---|---|---:|---:|---|
| `variant_sign_prior` (draw a / b) | reference + physical sign prior: of two sign-twin candidates, drop the one that cannot hold with positive quantities; rank such laws last | – | **+0.053 / +0.049** | single 0/0 · +7/−0 · +14/−0 (b: +13/−0); two 0/0 · +2/−0 · +4/−1; three 0/0 · +1/−0 · +2/−1 (b: +2/−2) |
| `variant_sign_dim_restate` | sign prior + top-dimensional components first + drop target restatements | – | +0.051 | as sign prior (draw a), except two-axiom unsound +3/−1 |
| `variant_saturate_extra_orders` | saturate before decomposing + generators in two more orders | +0.047 | +0.008 | within noise (single top-1 +4/−6, one extra two-axiom explanation) |
| `variant_extra_orders` | generators in two more monomial orders | +0.071 (+9/−0) | −0.002 | ties (single top-1 +2/−1, three-axiom unsound −2) |
| `variant_dim_rank` | top-dimensional components first (Theorem 1) | – | −0.004 | ties |
| `variant_canonical` (2 draws) | reduced Gröbner basis of each prime as generators | – | −0.023 | single top-1 +2/−8 |
| `variant_saturation_only` | one saturated component instead of a decomposition | −0.144 | −0.158 | single recovery −25, top-1 −15, unsound +22 |
| `weaker_unranked_singletons` | no strong/weak ranking, no degeneracy filter | −0.159 | −0.247 | unsound −35 / −37 / −19 |
| `weaker_no_reasoning` | no Reason step | −0.255 | −0.331 | single recovery −20, unsound −25 |
| `enumerative_baseline` | syntax-guided brute force | −0.434 | −0.628 | single recovery −36, two-axiom explanation −31 |
| `no_abduction_baseline` | proposes nothing | −0.621 | −0.929 | — |

**Why the extra-orders variant's advantage disappeared.** Its earlier +0.071
(9 paired wins, 0 losses) came entirely from instances where the old evaluator
misjudged the reference's correct candidates as unsound. Under the corrected
test the reference succeeds on all 9, so the variant ties.

**What headroom remains.** The sign-prior variant shows that more precise
abduction pays where the reference proposes false sign-twin laws next to the
true one.

**Noise.** Singular's `minAss` returns different generating sets for the same
prime components from run to run. This happens with a fixed `--random` seed and
also with address-space randomization disabled (`setarch -R`; 28 of 159 outputs
still differed). The official AI-Noether code behaves the same. Five reference
draws give `dW` = 0, +0.002, −0.004, −0.006, −0.006. Their paired differences
from the anchor are at most 3 instances on any metric, mostly top-1.

Reduced Gröbner bases per prime make the method fully deterministic (159/159
identical outputs across two runs) but cost 0.023. I kept the paper's raw
`minAss` generators, and the reference row is the median of three draws of the
final code. The sign-prior gain is about 10× the noise span, and the reference's
effect over the baselines (0.63 and 0.93) is far larger.

## Shortcuts

| Shortcut | Original gym (REDTEAM ΔW) | Previous evaluator (dW) | Fix | Final dW |
|---|---:|---:|---|---:|
| Read the hidden instance file during the run (`oracle_hidden_lookup`) | – | **+1.079** | private files off disk while solvers run | **−1.229** (crashes → worst values) |
| Search the workspace for any file holding the answers (`oracle_fs_search`) | – | – | same | −0.929 (finds nothing) |
| Replay answers from public complete systems / brute-force dictionary of public laws | +0.184 | n/a | held-out theories exist only in `eval/test` (first pass) | n/a; full-budget brute force on a 12-per-experiment subset: single recovery 0.833 vs reference 1.0; two- and three-axiom explanation 0.083 vs 0.500 / 0.417 |
| Fabricated problem definition | +0.184 | −0.621 | evaluator owns instances (first pass) | −0.929 |
| Contradiction `[1, hidden variable]` | +0.184 | −0.921 | soundness test | −1.229 (unsound everywhere) |
| Copy the target / append known axioms | +0.184 | −0.621 | nontriviality test | −0.929 |
| Target with nonzero factor divided out (`strip_target_factor`) | – | −0.702 | **fix 2**: needed once fix 1 counts such laws as sound | −0.929 (earns nothing) |
| Case multiplication / duplicate sets | +0.023 | dupe = reference on subset | fixed instance set; sets canonicalized; top-5 cap | duplicates equal the reference on the 8-per-experiment subset (no gain) |
| Omit cases, empty output, empty shape, unlisted or late method | tie (0) | worst everywhere | evaluator runs every solver on every fixed instance; failure = worst value | −1.229 (crash, `{}`, `null` sets) |
| Forged flags / prewritten score file | −0.758 | −0.621 | evaluator ignores solver fields and overwrites the score file | −0.929 |
| Oversized sets (target + all known axioms + `1`) | – | −0.626 | at most `num_missing` polynomials per set | −0.931 |
| Planted `Singular` binary on `PATH` | – | not run | **fix 5**: binary resolved to an absolute path outside the workspace before solvers run | not run (closed by construction) |
| Read the answers from git history (`oracle_git_lookup`) | – | – | **not closable by the evaluator** | **+0.451** (left) |

### Shortcuts left, and why

* **Answers from repository history** (+0.451 measured with `git show
  HEAD:eval/test/instances.json`). The theories and instances are committed, and
  the evaluator cannot change what a solver can read from `.git` or from any
  other copy outside the workspace. Whether this pays in the hidden test depends
  on whether its container carries the history. It is an unambiguous cheat
  (`scoring/CONSTRAINTS.md` forbids reading evaluator files) and is easy for the
  shortcut grader to detect.
* **Process-level interference.** A solver that kills the evaluator after
  writing a forged score file, or a background process that copies the
  temporary Singular scoring scripts, is not defended against. The task says not
  to build defenses against leftover processes. Every such attack is visible in
  the solver code.

## Reference before and after

| Slice | Experiment | Before: recovery / explanation / top-1 / unsound | After |
|---|---|---|---|
| test | single | 0.882 / 0.882 / 0.632 / 0.647 (68 inst.) | **1.000 / 1.000 / 0.844 / 0.344** (64) |
| test | two missing | 0 / 0.482 / 0.429 / 0.500 (56) | 0 / **0.655 / 0.600 / 0.145** (55) |
| test | three missing | 0 / 0.167 / 0.143 / 0.429 (42) | 0 / **0.300 / 0.275 / 0.050** (40) |
| train | single | 0.932 / 0.932 / 0.729 / 0.847 (59) | 1.000 / 1.000 / 0.845 / 0.466 (58) |
| train | two missing | 0.059 / 0.324 / 0.206 / 0.647 (34) | 0.088 / 0.500 / 0.353 / 0.206 (34) |
| train | three missing | 0 / 0.182 / 0.182 / 0.515 (33) | 0 / 0.394 / 0.303 / 0.061 (33) |

* The reference's code path is unchanged apart from opt-in flags. It and both
  baselines were rerun from the final code: test reference draws 2 and 3 used
  the final method code, and the baselines and train rows came from the round-1
  job, whose code path is identical.
* Train and test agree, and both reproduce the paper's direction: AI-Noether
  recovers single missing axioms (paper 73/75; here every well-posed removal),
  explains about half of the two-axiom removals (paper 105/215; here 0.50 train,
  0.66 test) and fewer three-axiom removals (paper 109/383; here 0.39 / 0.30).
  The empty and enumerative baselines score far below, as the paper reports for
  its LLM and cvc5 baselines.
* `scoring/scores_test.json` holds only the gym's three solvers. Shortcut and
  variant scores are in `hardening/`.

## Headroom check

**Scored metrics at the bound for the reference:**
* single-axiom `recovery_rate` = 1.0
* single-axiom `explanation_rate` = 1.0

**Below the bound:**
* single-axiom top-1 0.844 and unsound 0.344
* two-axiom explanation 0.655, top-1 0.600, unsound 0.145
* three-axiom explanation 0.300, top-1 0.275, unsound 0.050

Every instance is solvable: the oracle scores 1 everywhere.

**Demonstrated:** the sign-prior variant scores above the reference by about 10×
the noise. It improves single-axiom top-1 (0.844 → 0.953) and unsound
(0.344 → 0.125), and multi-axiom top-1 and unsound. It is still well below the
bound.

**Not demonstrated:** headroom in multi-axiom *explanation* (0.655 / 0.300
against 1.0). None of the honest variants I tried raised it: extra monomial
orders, saturation, dimension ranking, canonical generators, dropping
restatements, or the sign prior. Of the reference's misses, 22 two/three-axiom instances had no
usable generator at all, and 17 offered only target restatements. A better
multi-axiom method is the open research direction (`scoring/DIRECTION.md`). I
did not add an experiment, because the reference is not at the bound of every
scored metric.

**Brute force:** enumeration given the full 60 s per instance does not solve the
test or outrank the reference (subset figures in the shortcut table). The
default enumerative baseline is clearly below the reference on every benefit
metric.

## What I could not fix

* The git-history answer leak (above).
* Reference nondeterminism. It is inherent to Singular's `minAss` and the
  official code; canonicalizing the generators would make the reference
  deterministic but weaker and not the paper's procedure.
* Multi-axiom decoupled recovery is out of reach on the single-target held-out
  theories and is therefore unscored. The paper obtains decoupled recovery with
  multiple consequences (Section 3.3); the held-out slice has no multi-target
  theory.
* Inherited scope limits, not changed here:
  * The paper's noisy pathway (numerical decomposition, symbolic regression,
    KeYmaera X) and its cvc5 / GPT-5 Pro baselines are not reproduced.
  * Train keeps only the well-posed removals of the paper's systems (58 of the
    paper's 75 single removals).
  * The per-instance limit is 60 s instead of 7200 s. The reference needs at
    most about 6 s per held-out instance.

## Reproducing

* `bash scripts/run.sh` rebuilds missing instances, evaluates every solver on
  train and on the hidden test, and validates.
* `bash scripts/evaluate_test.sh` (no arguments) is the hidden test.
* The audit probes: `python eval/test/evaluate.py --solvers-dir
  hardening/solvers_<set> --output hardening/scores_test_<set>.json`, then
  `python hardening/summarize.py`.
