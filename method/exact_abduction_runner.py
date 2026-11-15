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
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from polyutil import Poly, PolyError, parse_poly  # noqa: E402

SINGULAR = os.environ.get("SINGULAR_BIN", "Singular")
GEN_LIMITS = {"max_terms": 4000, "max_degree": 80, "max_exponent": 80, "max_chars": 200000, "max_int_digits": 400}
CHUNK = 25


class Deadline:
    def __init__(self, seconds: float):
        self.end = time.monotonic() + seconds

    def left(self) -> float:
        return self.end - time.monotonic()


_NO_ASLR: list | None = None


def no_aslr_prefix() -> list:
    """['setarch', <arch>, '-R'] when AINOETHER_NO_ASLR=1 and it works here, else []."""
    global _NO_ASLR
    if _NO_ASLR is None:
        _NO_ASLR = []
        if os.environ.get("AINOETHER_NO_ASLR") == "1" and shutil.which("setarch"):
            prefix = ["setarch", platform.machine(), "-R"]
            try:
                ok = subprocess.run(prefix + ["true"], capture_output=True, timeout=10).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            if ok:
                _NO_ASLR = prefix
    return _NO_ASLR


def run_singular(script: str, timeout: float, seed: int) -> str:
    with tempfile.TemporaryDirectory(prefix="ainoether_") as td:
        path = Path(td) / "job.sing"
        path.write_text(script)
        cmd = [SINGULAR, "-q", f"--random={seed}", str(path)]
        if no_aslr_prefix():
            # Singular's minAss output can depend on memory layout; a fixed layout
            # makes repeated runs return the same generators.
            cmd = no_aslr_prefix() + cmd
        proc = subprocess.run(
            cmd,
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
    kt = "KNOWN + TARG"
    if opts.drop_restatements:
        stripped = [strip_nonzero_content(q, variables, nonzero) for q in inst["targets"]]
        kt += " + ideal(" + ", ".join(stripped) + ")"
    degen = []
    if opts.prune_degenerate:
        # Appendix E.2: a component on which a physically nonzero quantity (or 1)
        # vanishes describes a boundary case; its generators are not proposed.
        degen = ["  PS = std(P); dg = 0;", "  if (size(reduce(one, PS)) == 0) { dg = 1; }"]
        degen += [f"  if (size(reduce({v}, PS)) == 0) {{ dg = 1; }}" for v in nonzero]
        degen.append('  print("DEGEN " + string(ci) + " " + string(dg));')
    lines += [
        f"ideal KT = std({kt});",
        "int ci; int gi; poly g; int us; ideal P;" + (" ideal PS; int dg; poly one = 1;" if degen else ""),
        "option(redSB);" if opts.canonical else "",
        'print("NCOMP " + string(size(M)));',
        "for (ci = 1; ci <= size(M); ci++) {",
        "  P = std(M[ci]);" if opts.canonical else "  P = M[ci];",
        '  print("DIM " + string(ci) + " " + string(dim(std(P))));' if opts.dim_rank else "",
        *degen,
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


def strip_nonzero_content(expr: str, names: list[str], nonzero: list[str]) -> str:
    """Divide a polynomial by its largest monomial factor in nonzero variables."""
    poly = parse_poly(expr, names, GEN_LIMITS)
    nz = {names.index(v) for v in nonzero if v in names}
    mins = [min(e[i] for e in poly.terms) if i in nz else 0 for i in range(poly.nvars)]
    return Poly(poly.nvars, {tuple(a - b for a, b in zip(e, mins)): c for e, c in poly.terms.items()}).to_string(names)


def parse_components(output: str, variables: list[str], dims: dict | None = None) -> tuple[int, list[list[str]], int]:
    comps: dict[int, list[str]] = {}
    total = 0
    ncomp = 0
    degenerate = {int(ln.split()[1]) for ln in output.splitlines()
                  if ln.startswith("DEGEN ") and len(ln.split()) == 3 and ln.split()[2] == "1"}
    for line in output.splitlines():
        parts = line.strip().split(" ", 3)
        if parts and parts[0] == "NCOMP" and len(parts) >= 2:
            ncomp = int(parts[1])
        if len(parts) == 4 and parts[0] == "GEN" and int(parts[1]) in degenerate:
            total += 1
            continue
        if dims is not None and len(parts) == 3 and parts[0] == "DIM":
            dims[int(parts[1])] = int(parts[2])
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
    keys = sorted(comps)
    if dims is not None:
        # keep each component's dimension aligned with the returned list
        aligned = {i: dims.get(k, -1) for i, k in enumerate(keys)}
        dims.clear()
        dims.update(aligned)
    return ncomp, [comps[k] for k in keys], total


def candidate_sets(components: list[list[str]], max_size: int, max_sets: int,
                   origin: dict | None = None) -> list[list[str]]:
    seen: set[frozenset] = set()
    out: list[list[str]] = []
    for size in range(1, max_size + 1):
        for ci, comp in enumerate(components):
            for subset in itertools.combinations(comp, size):
                key = frozenset(subset)
                if len(key) != size or key in seen:
                    continue
                seen.add(key)
                if origin is not None:
                    origin[len(out)] = ci
                out.append(list(subset))
                if len(out) >= max_sets:
                    return out
    return out


def candidate_sets_best_first(components: list[list[str]], max_size: int, max_sets: int, variables: list[str],
                              origin: dict | None = None) -> list[list[str]]:
    """Variant: test the simplest subsets first instead of all subsets in index order.

    Generator cost = number of terms + total degree.  Each component keeps its
    N simplest generators (N as large as the budget allows for subsets up to
    max_size); all their subsets are visited in order of total cost."""
    def cost(text: str) -> int:
        poly = parse_poly(text, variables, GEN_LIMITS)
        return poly.num_terms() + poly.total_degree()

    def n_subsets(n: int) -> int:
        from math import comb
        return sum(comb(n, k) for k in range(1, max_size + 1))

    keep = 1
    while n_subsets(keep + 1) <= max_sets:
        keep += 1
    pool = []
    for ci, comp in enumerate(components):
        ranked = sorted(comp, key=lambda g: (cost(g), g))[:keep]
        costs = [cost(g) for g in ranked]
        for size in range(1, min(max_size, len(ranked)) + 1):
            for idx in itertools.combinations(range(len(ranked)), size):
                pool.append((sum(costs[i] for i in idx), size, ci, idx, [ranked[i] for i in idx]))
    pool.sort(key=lambda x: x[:4])
    seen: set[frozenset] = set()
    out: list[list[str]] = []
    for _c, _size, ci, _idx, subset in pool:
        key = frozenset(subset)
        if key in seen:
            continue
        seen.add(key)
        if origin is not None:
            origin[len(out)] = ci
        out.append(subset)
        if len(out) >= max_sets:
            break
    return out


def generator_cost(text: str, variables: list[str]) -> int:
    poly = parse_poly(text, variables, GEN_LIMITS)
    return poly.num_terms() + poly.total_degree()


def greedy_closure_sets(inst: dict, components: list[list[str]], max_size: int, deadline: "Deadline",
                        seed: int) -> list[list[str]]:
    """Variant: complete each component greedily (Theorem 1 guided).

    If the observed laws determine the missing axioms, a prime component of
    <known, laws> contains them.  Walk the component's generators simplest
    first and keep a generator only when it is not already implied by the known
    axioms and the generators kept so far (wherever the nonzero quantities are
    nonzero); stop after max_size kept generators.  Each component yields one
    candidate set of independent simple laws."""
    variables = inst["variables"]
    nonzero = inst.get("nonzero_variables") or []
    hnz = "*".join(nonzero) if nonzero else "1"
    lines = [f"ring R = 0, (t, {', '.join(variables)}), dp;", "short = 0;"]
    for i, a in enumerate(inst["known_axioms"], 1):
        lines.append(f"poly k{i} = {a};")
    known = ", ".join(f"k{i}" for i in range(1, len(inst["known_axioms"]) + 1)) or "0"
    lines += [f"ideal KNOWN = {known};", "ideal S; ideal G; int cnt; poly g;"]
    order: dict[int, list[str]] = {}
    for ci, comp in enumerate(components):
        ranked = sorted(comp, key=lambda g: (generator_cost(g, variables), g))
        order[ci] = ranked
        lines += ["S = KNOWN;", f"G = std(S + ideal(1 - t*{hnz}));", "cnt = 0;"]
        for gi, g in enumerate(ranked):
            lines += [f"g = {g};",
                      f"if (cnt < {max_size}) {{ if (size(reduce(g, G)) != 0) {{ S = S + ideal(g); "
                      f"G = std(S + ideal(1 - t*{hnz})); cnt = cnt + 1; print(\"GREEDY {ci} {gi}\"); }} }}"]
    lines.append("quit;")
    if deadline.left() < 2.0:
        return []
    out = run_singular("\n".join(lines) + "\n", deadline.left() - 1.0, seed)
    picked: dict[int, list[str]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "GREEDY":
            ci, gi = int(parts[1]), int(parts[2])
            picked.setdefault(ci, []).append(order[ci][gi])
    return [picked[ci] for ci in sorted(picked)]


def sparse_laws(inst: dict, deadline: "Deadline", seed: int, pool: int = 40) -> list[str]:
    """Variant: two-term laws of the abduced ideal.

    Saturate <known axioms, targets> by the product of the nonzero quantities
    (every element is then a law wherever those quantities are nonzero), compute
    normal forms of all monomials up to degree 3 or 4, and read off every
    binomial c1*m1 - c2*m2 (coprime monomials with proportional normal forms).
    The simplest ones not already in <known, targets, stripped targets> form one
    extra candidate component."""
    from fractions import Fraction
    from math import comb
    variables = inst["variables"]
    n = len(variables)
    nonzero = inst.get("nonzero_variables") or []
    hnz = "*".join(nonzero) if nonzero else "1"
    deg = 4 if comb(n + 4, 4) <= 1500 else 3
    monos = [tuple([0] * n)]
    for d in range(1, deg + 1):
        for combo in itertools.combinations_with_replacement(range(n), d):
            exp = [0] * n
            for i in combo:
                exp[i] += 1
            monos.append(tuple(exp))

    def mono(exp) -> str:
        return "*".join((variables[i] if e == 1 else f"{variables[i]}^{e}") for i, e in enumerate(exp) if e) or "1"

    known = ", ".join(inst["known_axioms"]) or "0"
    targets = ", ".join(inst["targets"])
    lines = [f"ring R = 0, (t, {', '.join(variables)}), dp;", "short = 0;",
             f"ideal SAT = eliminate(ideal({known}) + ideal({targets}) + ideal(1 - t*{hnz}), t);",
             f"ring S = 0, ({', '.join(variables)}), dp;", "short = 0;", "option(redSB);",
             "ideal SG = std(imap(R, SAT));"]
    lines += [f'print("NF {k} " + string(reduce(poly({mono(m)}), SG)));' for k, m in enumerate(monos)]
    lines.append("quit;")
    if deadline.left() < 3.0:
        return []
    out = run_singular("\n".join(lines) + "\n", 0.5 * deadline.left(), seed)
    limits = dict(GEN_LIMITS, max_terms=20000, max_chars=2000000, max_degree=200, max_exponent=200)
    groups: dict = {}
    for line in out.splitlines():
        parts = line.split(" ", 2)
        if len(parts) != 3 or parts[0] != "NF":
            continue
        nf = parse_poly(parts[2], variables, limits)
        if nf.is_zero():
            continue
        lead = max(nf.terms, key=lambda e: (sum(e), e))
        c = nf.terms[lead]
        groups.setdefault(tuple(sorted((e, v / c) for e, v in nf.terms.items())), []).append((monos[int(parts[1])], c))
    found = []
    for members in groups.values():
        for (m1, c1), (m2, c2) in itertools.combinations(members, 2):
            if any(a and b for a, b in zip(m1, m2)):
                continue
            poly = Poly(n, {m1: Fraction(c2), m2: -Fraction(c1)})
            found.append((max(sum(m1), sum(m2)), sum(m1) + sum(m2), poly.to_string(variables)))
    found.sort()
    cands = [f[2] for f in found[: 4 * pool]]
    if not cands or deadline.left() < 2.0:
        return []
    stripped = [strip_nonzero_content(q, variables, nonzero) for q in inst["targets"]]
    lines = [f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;",
             f"ideal KT = std(ideal({known}) + ideal({targets}) + ideal({', '.join(stripped)}));"]
    lines += [f'print("NT {k} " + string(size(reduce({g}, KT)) != 0));' for k, g in enumerate(cands)]
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", deadline.left() - 1.0, seed)
    keep = {int(p[1]) for p in (ln.split() for ln in out.splitlines()) if len(p) == 3 and p[0] == "NT" and p[2] == "1"}
    return [g for k, g in enumerate(cands) if k in keep][:pool]


def sign_definite(text: str, variables: list[str]) -> bool:
    """True when all coefficients share one sign: no solution with all quantities positive."""
    poly = parse_poly(text, variables, GEN_LIMITS)
    signs = {c > 0 for c in poly.terms.values()}
    return len(signs) == 1


def twin_key(polys, variables: list[str]) -> frozenset:
    """A set's polynomials up to the signs of their individual terms."""
    out = []
    for text in polys:
        poly = parse_poly(text, variables, GEN_LIMITS)
        out.append(tuple(sorted((e, abs(c)) for e, c in poly.integer_primitive().items())))
    return frozenset(out)


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
    dims: dict = {}
    ncomp, components, total = parse_components(out, variables, dims)
    if opts.canonical:
        # reduced Groebner bases are unique: order components canonically too
        order = sorted(range(len(components)), key=lambda i: sorted(components[i]))
        components = [sorted(components[i]) for i in order]
        dims = {new: dims.get(old, -1) for new, old in enumerate(order)}
    if opts.dim_rank:
        # Theorem 1 (Section 3.5): the prime shared with the complete theory has
        # the minimal height, i.e. the top dimension; visit those components first.
        order = sorted(range(len(components)), key=lambda i: -dims.get(i, -1))
        components = [components[i] for i in order]
        dims = {new: dims.get(old, -1) for new, old in enumerate(order)}
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
    if opts.sparse_laws:
        sparse = sparse_laws(inst, deadline, opts.seed)
        diag["sparse_laws"] = len(sparse)
        if sparse:
            components = [sparse] + components
            dims = {i + 1: d for i, d in dims.items()}
    origin: dict = {}
    if opts.best_first:
        sets = candidate_sets_best_first(components, max_size, opts.max_sets, variables, origin)
    else:
        sets = candidate_sets(components, max_size, opts.max_sets, origin)
    if opts.greedy_closure:
        greedy = greedy_closure_sets(inst, components, max_size, deadline, opts.seed)
        diag["greedy_sets"] = len(greedy)
        known_keys = {frozenset(x) for x in sets}
        extra = [g for g in greedy if frozenset(g) not in known_keys]
        # greedy completions are tested first; the budget stays max_sets
        sets = (extra + sets)[: opts.max_sets]
        origin = {}
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
    if opts.dim_rank:
        top = max(dims.values(), default=-1)
        ranked = sorted(ranked, key=lambda item: dims.get(origin.get(item[0], -1), -1) < top)  # stable
    if opts.sign_prior:
        # Physical sign prior: a law whose terms all share one sign has no solution
        # with all quantities positive.  Among sign twins (same terms, different
        # signs) keep only the members with the fewest such laws; rank sets
        # without them first.
        definite = {k: sum(sign_definite(p, variables) for p in s) for k, s in ranked}
        groups: dict = {}
        for k, s in ranked:
            groups.setdefault(twin_key(s, variables), []).append(k)
        keep = set()
        for members in groups.values():
            best = min(definite[k] for k in members)
            keep.update(k for k in members if definite[k] == best)
        ranked = sorted([x for x in ranked if x[0] in keep], key=lambda item: definite[item[0]] > 0)
        diag["sign_twins_dropped"] = len(definite) - len(keep)
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
    parser.add_argument("--canonical", action="store_true",
                        help="variant: reduced Groebner basis of each prime as its generators (unique, run-independent)")
    parser.add_argument("--dim-rank", action="store_true",
                        help="variant: rank candidates from top-dimensional components first (Theorem 1)")
    parser.add_argument("--sign-prior", action="store_true",
                        help="variant: drop sign twins that cannot hold with positive quantities and rank them last")
    parser.add_argument("--drop-restatements", action="store_true",
                        help="variant: also drop generators that restate the target divided by nonzero quantities")
    parser.add_argument("--prune-degenerate", action="store_true",
                        help="variant: drop components on which a declared nonzero quantity vanishes")
    parser.add_argument("--best-first", action="store_true",
                        help="variant: visit candidate subsets simplest first (same budget of --max-sets)")
    parser.add_argument("--sparse-laws", action="store_true",
                        help="variant: add two-term laws of the saturated <known, targets> as one more component")
    parser.add_argument("--greedy-closure", action="store_true",
                        help="variant: also test, per component, the greedy completion by independent simplest generators")
    opts = parser.parse_args()

    inst = json.loads(Path(opts.instance).read_text())
    deadline = Deadline(max(3.0, opts.time_limit - opts.margin))
    diag: dict = {}
    try:
        sets = solve(inst, opts, deadline, diag)
    except Exception as exc:  # noqa: BLE001 - report an empty, well-formed answer
        diag["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        sets = []
    diag["no_aslr"] = bool(no_aslr_prefix())
    payload = {"method": opts.method_name, "candidate_sets": sets, "diagnostics": diag}
    out = Path(opts.output)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    tmp.replace(out)


if __name__ == "__main__":
    main()
