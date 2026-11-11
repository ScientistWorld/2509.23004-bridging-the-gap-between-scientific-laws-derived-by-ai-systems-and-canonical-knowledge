#!/usr/bin/env python3
"""AI-Noether exact abduction (Encode - Decompose - Reason) for one instance.

Implements the noiseless branch of the paper's Algorithm 1 (Appendix E.3):

  Encode     I = <A_1, ..., A_k, Q_1, ..., Q_s>  (known axioms + targets)
  Decompose  minimal associated primes of I (Singular ``minAss``); the
             generators of every prime component are candidate axioms.
             Generators already in <known axioms, targets> carry no new
             information and are dropped (as in the official code).
  Reason     each subset of one component's generators (size <= number of
             missing axioms) is added to the known axioms.  It is accepted
             when every target lies in the projection of the augmented ideal
             onto the target's measured variables (weak test, ideal
             membership) and it does not force a declared nonzero quantity to
             zero (Appendix E.2 degeneracy filtering).  The strong test checks
             that the target itself appears in the reduced lexicographic
             Groebner basis of that projection.

Output ranking follows the paper's two tiers: inclusion-minimal strong sets
first (high confidence), then the remaining minimal weak sets; ties are broken
by parsimony.  All Groebner basis work runs in Singular.

Usage: exact_abduction_runner.py --instance in.json --output out.json
The per-instance time budget is read from ABDUCTION_TIME_LIMIT (seconds).
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from polyutil import PolyError, parse_poly  # noqa: E402

SINGULAR = os.environ.get("SINGULAR_BIN", "Singular")
GEN_LIMITS = {"max_terms": 4000, "max_degree": 80, "max_exponent": 80, "max_chars": 200000, "max_int_digits": 400}
CHUNK = 25


class Deadline:
    def __init__(self, seconds: float):
        self.end = time.monotonic() + seconds

    def left(self) -> float:
        return self.end - time.monotonic()


def run_singular(script: str, timeout: float, seed: int) -> str:
    with tempfile.TemporaryDirectory(prefix="ainoether_") as td:
        path = Path(td) / "job.sing"
        path.write_text(script)
        proc = subprocess.run(
            [SINGULAR, "-q", f"--random={seed}", str(path)],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=max(1.0, timeout),
            check=False,
        )
    errors = [ln.strip() for ln in (proc.stdout + '\n' + proc.stderr).splitlines() if ln.strip().startswith('?')]
    if errors:
        raise RuntimeError('Singular error: ' + ' | '.join(errors[:4]))
    if proc.returncode != 0:
        raise RuntimeError(f"Singular exit {proc.returncode}: {proc.stderr[-800:]}")
    return proc.stdout


def poly_lines(inst: dict) -> list[str]:
    lines = []
    for i, a in enumerate(inst["known_axioms"], 1):
        lines.append(f"poly k{i} = {a};")
    for j, q in enumerate(inst["targets"], 1):
        lines.append(f"poly q{j} = {q};")
    known = ", ".join(f"k{i}" for i in range(1, len(inst["known_axioms"]) + 1)) or "0"
    targ = ", ".join(f"q{j}" for j in range(1, len(inst["targets"]) + 1))
    lines += [f"ideal KNOWN = {known};", f"ideal TARG = {targ};"]
    return lines


# ---------------------------------------------------------------- Decompose
def decomposition_script(inst: dict, opts) -> str:
    variables = inst["variables"]
    lines = ['LIB "primdec.lib";', f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;"]
    lines += poly_lines(inst)
    lines.append("ideal ENC = KNOWN + TARG;")
    nonzero = inst.get("nonzero_variables") or []
    if opts.saturate and nonzero:
        lines += [
            f"ring Rt = 0, (t, {', '.join(variables)}), dp;",
            "ideal ENCt = imap(R, ENC);",
            f"ENCt = ENCt + ideal(1 - t*{'*'.join(nonzero)});",
            "ideal SATt = eliminate(ENCt, t);",
            "setring R;",
            "ENC = imap(Rt, SATt);",
        ]
    if opts.saturation_only:
        sat = "*".join(nonzero) if nonzero else "1"
        lines += [
            f"ring Rs = 0, (t, {', '.join(variables)}), dp;",
            f"ideal SATs = eliminate(imap(R, ENC) + ideal(1 - t*{sat}), t);",
            "setring R;",
            "option(redSB);",
            "list M = list(std(imap(Rs, SATs)));",
        ]
    else:
        lines.append("list M = minAss(ENC);")
    lines += [
        "ideal KT = std(KNOWN + TARG);",
        "int ci; int gi; poly g; int us; ideal P;",
        'print("NCOMP " + string(size(M)));',
        "for (ci = 1; ci <= size(M); ci++) {",
        "  P = M[ci];",
        "  for (gi = 1; gi <= ncols(P); gi++) {",
        "    g = P[gi];",
        "    if (g != 0) {",
        "      us = (size(reduce(g, KT)) != 0);",
        '      print("GEN " + string(ci) + " " + string(us) + " " + string(g));',
        "    }",
        "  }",
        "}",
    ]
    if opts.extra_orders:
        measured = [v for v in variables if v in set(inst["measured_variables"])]
        hidden = [v for v in variables if v not in set(inst["measured_variables"])]
        orders = [("O1", list(reversed(variables)), "dp"), ("O2", hidden + measured, "lp")]
        for tag, order, ordering in orders:
            lines += [
                f"ring {tag} = 0, ({', '.join(order)}), {ordering};",
                "option(redSB);",
                f"ideal P{tag}; poly g{tag};",
                "setring R;",
                f"ideal B{tag};",
                "for (ci = 1; ci <= size(M); ci++) {",
                "  P = M[ci];",
                f"  setring {tag};",
                f"  P{tag} = std(imap(R, P));",
                "  setring R;",
                f"  B{tag} = imap({tag}, P{tag});",
                f"  for (gi = 1; gi <= ncols(B{tag}); gi++) {{",
                f"    g = B{tag}[gi];",
                "    if (g != 0) {",
                "      us = (size(reduce(g, KT)) != 0);",
                '      print("GEN " + string(ci) + " " + string(us) + " " + string(g));',
                "    }",
                "  }",
                "}",
            ]
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def parse_components(output: str, variables: list[str]) -> tuple[int, list[list[str]], int]:
    comps: dict[int, list[str]] = {}
    total = 0
    ncomp = 0
    for line in output.splitlines():
        parts = line.strip().split(" ", 3)
        if parts and parts[0] == "NCOMP" and len(parts) >= 2:
            ncomp = int(parts[1])
        if len(parts) == 4 and parts[0] == "GEN":
            total += 1
            if parts[2] != "1":
                continue
            try:
                poly = parse_poly(parts[3], variables, GEN_LIMITS)
            except PolyError:
                continue
            if poly.is_zero() or poly.is_constant():
                continue
            canon = poly.to_string(variables)
            bucket = comps.setdefault(int(parts[1]), [])
            if canon not in bucket:
                bucket.append(canon)
    return ncomp, [comps[k] for k in sorted(comps)], total


def candidate_sets(components: list[list[str]], max_size: int, max_sets: int) -> list[list[str]]:
    seen: set[frozenset] = set()
    out: list[list[str]] = []
    for size in range(1, max_size + 1):
        for comp in components:
            for subset in itertools.combinations(comp, size):
                key = frozenset(subset)
                if len(key) != size or key in seen:
                    continue
                seen.add(key)
                out.append(list(subset))
                if len(out) >= max_sets:
                    return out
    return out


# ------------------------------------------------------------------- Reason
def reasoning_script(inst: dict, sets: list[list[str]], offset: int, opts) -> str:
    variables = inst["variables"]
    measured = set(inst["measured_variables"])
    lines = [f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;", "option(redSB);", "poly one = 1;"]
    lines += poly_lines(inst)
    lines.append("ideal J; ideal E; int w; int d; int s; int sj; int i;")
    target_info = []
    for j, q in enumerate(inst["targets"], 1):
        qp = parse_poly(q, variables, GEN_LIMITS)
        qvars = [variables[i] for i in sorted(qp.used_variables()) if variables[i] in measured]
        elim = [v for v in variables if v not in set(qvars)]
        target_info.append((j, qvars, elim))
        if qvars:
            lines += [f"ring Q{j} = 0, ({', '.join(qvars)}), lp;", f"ideal EQ{j}; poly QQ{j} = imap(R, q{j});", "setring R;"]
    nonzero = inst.get("nonzero_variables") or []
    for k, cand in enumerate(sets):
        lines.append(f"J = std(KNOWN + ideal({', '.join(cand)}));")
        lines.append("w = 1;")
        for j, _qv, _el in target_info:
            lines.append(f"if (size(reduce(q{j}, J)) != 0) {{ w = 0; }}")
        lines.append("d = 0;")
        if not opts.no_degenerate_filter:
            lines.append("if (size(reduce(one, J)) == 0) { d = 1; }")
            for v in nonzero:
                lines.append(f"if (size(reduce({v}, J)) == 0) {{ d = 1; }}")
        lines.append("s = 0;")
        lines.append("if ((w == 1) && (d == 0)) {")
        lines.append("  s = 1;")
        for j, qvars, elim in target_info:
            if not qvars:
                lines.append("  s = 0;")
                continue
            lines.append(f"  E = eliminate(J, {'*'.join(elim)});" if elim else "  E = J;")
            lines += [
                f"  setring Q{j};",
                f"  EQ{j} = std(imap(R, E));",
                "  sj = 0;",
                f"  for (i = 1; i <= ncols(EQ{j}); i++) {{",
                f"    if (EQ{j}[i] != 0) {{",
                f"      if (deg(EQ{j}[i]) == deg(QQ{j})) {{",
                f"        if (size(reduce(QQ{j}, std(ideal(EQ{j}[i])))) == 0) {{ sj = 1; }}",
                "      }",
                "    }",
                "  }",
                "  setring R;",
                "  if (sj == 0) { s = 0; }",
            ]
        lines.append("}")
        lines.append(f'print("SET {offset + k} " + string(w) + " " + string(d) + " " + string(s));')
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def minimal(sets: list[tuple[int, frozenset]]) -> list[tuple[int, frozenset]]:
    return [(k, s) for k, s in sets if not any(o < s for _k, o in sets)]


def solve(inst: dict, opts, deadline: Deadline, diag: dict) -> list[list[str]]:
    variables = inst["variables"]
    max_size = opts.max_set_size or int(inst["num_missing"])
    t0 = time.monotonic()
    out = run_singular(decomposition_script(inst, opts), max(2.0, opts.decomp_share * deadline.left()), opts.seed)
    ncomp, components, total = parse_components(out, variables)
    diag.update({"components": ncomp, "generators": total, "usable_generators": sum(map(len, components)),
                 "decompose_seconds": round(time.monotonic() - t0, 2)})
    if opts.no_reason:
        # Ablation: skip the Reason step and return every usable generator.
        flat = []
        for comp in components:
            for g in comp:
                if [g] not in flat:
                    flat.append([g])
        diag["candidate_sets"] = len(flat)
        return flat
    sets = candidate_sets(components, max_size, opts.max_sets)
    diag["candidate_sets"] = len(sets)
    flags: dict[int, tuple[bool, bool, bool]] = {}
    t1 = time.monotonic()
    for start in range(0, len(sets), CHUNK):
        if deadline.left() < 1.5:
            diag["reason_truncated"] = True
            break
        chunk = sets[start:start + CHUNK]
        try:
            res = run_singular(reasoning_script(inst, chunk, start, opts), deadline.left() - 0.5, opts.seed)
        except subprocess.TimeoutExpired:
            diag["reason_truncated"] = True
            break
        except RuntimeError as exc:
            diag.setdefault("reason_errors", []).append(str(exc)[:200])
            continue
        for line in res.splitlines():
            parts = line.split()
            if len(parts) == 5 and parts[0] == "SET":
                flags[int(parts[1])] = (parts[2] == "1", parts[3] == "1", parts[4] == "1")
    diag["reason_seconds"] = round(time.monotonic() - t1, 2)
    diag["sets_tested"] = len(flags)
    accepted = [(k, frozenset(sets[k])) for k in sorted(flags) if flags[k][0] and not flags[k][1]]
    strong = [(k, s) for k, s in accepted if flags[k][2]]
    diag["accepted"] = len(accepted)
    diag["strong"] = len(strong)

    def parsimony(item: tuple[int, frozenset]):
        k, s = item
        polys = [parse_poly(p, variables, GEN_LIMITS) for p in s]
        return (len(s), sum(p.num_terms() for p in polys), max(p.total_degree() for p in polys), k)

    if opts.no_rank:
        ranked = minimal(accepted)
    else:
        strong_min = sorted(minimal(strong), key=parsimony)
        strong_keys = {s for _k, s in strong_min}
        weak_min = sorted([x for x in minimal(accepted) if x[1] not in strong_keys], key=parsimony)
        ranked = strong_min + weak_min
    return [list(sets[k]) for k, _s in ranked]


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Noether exact abduction for one instance")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--time-limit", type=float, default=float(os.environ.get("ABDUCTION_TIME_LIMIT", "60")))
    parser.add_argument("--margin", type=float, default=6.0, help="seconds kept free before the time limit")
    parser.add_argument("--seed", type=int, default=1, help="Singular random seed")
    parser.add_argument("--max-set-size", type=int, default=0, help="0 = number of missing axioms")
    parser.add_argument("--max-sets", type=int, default=400)
    parser.add_argument("--decomp-share", type=float, default=0.7, help="share of the budget for decomposition")
    parser.add_argument("--method-name", default="ai_noether_exact")
    # Variants used for gym hardening checks (defaults reproduce the paper's procedure).
    parser.add_argument("--saturate", action="store_true", help="saturate by nonzero variables before decomposing")
    parser.add_argument("--extra-orders", action="store_true", help="add generators from other monomial orders")
    parser.add_argument("--no-rank", action="store_true", help="skip strong/weak tiers and parsimony ranking")
    parser.add_argument("--no-degenerate-filter", action="store_true")
    parser.add_argument("--no-reason", action="store_true", help="ablation: output generators without reasoning")
    parser.add_argument("--saturation-only", action="store_true",
                        help="alternative: one saturated component instead of primary decomposition")
    opts = parser.parse_args()

    inst = json.loads(Path(opts.instance).read_text())
    deadline = Deadline(max(3.0, opts.time_limit - opts.margin))
    diag: dict = {}
    try:
        sets = solve(inst, opts, deadline, diag)
    except Exception as exc:  # noqa: BLE001 - report an empty, well-formed answer
        diag["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        sets = []
    payload = {"method": opts.method_name, "candidate_sets": sets, "diagnostics": diag}
    out = Path(opts.output)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    tmp.replace(out)


if __name__ == "__main__":
    main()
