#!/usr/bin/env python3
"""Enumerative abduction baseline (syntax-guided brute force).

A stand-in for the solver-based abduction baseline of the paper (cvc5 with a
SyGuS grammar): enumerate candidate axioms from a fixed grammar, simplest
first, and keep those that make every target derivable from the known axioms.

Grammar: single variables (``x = 0`` laws) and binomials ``a*m1 +/- b*m2`` with
monomials of total degree <= 2 and small coprime integer constants
(a, b) from {1, 2, 3, 4, 9}.  Candidates are checked in Singular batches:
  * nontrivial: not already in <known axioms, targets>;
  * derives:   every target lies in <known axioms, candidate>;
  * not degenerate: does not force a declared nonzero variable (or 1) to zero.
For multi-axiom instances the same single-polynomial grammar is used (coupled
explanations).  The search stops after ENUM_MAX_CANDIDATES grammar candidates
(0 = no count limit; the gym's baseline solver sets 6000 so its result does not
depend on machine speed) or at its time budget (ENUM_BUDGET seconds, default 5,
never more than the instance time limit minus a safety margin), whichever comes
first, and returns the first accepted candidates.

Usage: enumerative_abduction.py --instance in.json --output out.json
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
from math import gcd
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from polyutil import Poly  # noqa: E402

SINGULAR = os.environ.get("SINGULAR_BIN", "Singular")
CONSTS = [1, 2, 3, 4, 9]
BATCH = 300
MAX_ACCEPT = 5


def monomials(n: int, max_deg: int) -> list[tuple[int, ...]]:
    out = []
    for deg in range(1, max_deg + 1):
        for combo in itertools.combinations_with_replacement(range(n), deg):
            exp = [0] * n
            for i in combo:
                exp[i] += 1
            out.append(tuple(exp))
    return out


def candidates(n: int, names: list[str]):
    for i in range(n):
        yield names[i]
    monos = monomials(n, 2)
    pairs = sorted(
        ((a, b) for a in CONSTS for b in CONSTS if gcd(a, b) == 1),
        key=lambda ab: (max(ab), ab),
    )
    by_deg: dict[int, list[tuple]] = {}
    for m1, m2 in itertools.combinations(monos, 2):
        by_deg.setdefault(sum(m1) + sum(m2), []).append((m1, m2))
    for total in sorted(by_deg):
        for a, b in pairs:
            for m1, m2 in by_deg[total]:
                for sign in (-1, 1):
                    p = Poly(n, {m1: a, m2: sign * b})
                    yield p.to_string(names)


def batch_script(inst: dict, batch: list[str], offset: int) -> str:
    variables = inst["variables"]
    lines = [f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;", "poly one = 1;"]
    for i, a in enumerate(inst["known_axioms"], 1):
        lines.append(f"poly k{i} = {a};")
    for j, q in enumerate(inst["targets"], 1):
        lines.append(f"poly q{j} = {q};")
    known = ", ".join(f"k{i}" for i in range(1, len(inst["known_axioms"]) + 1)) or "0"
    targ = ", ".join(f"q{j}" for j in range(1, len(inst["targets"]) + 1))
    lines += [f"ideal KNOWN = {known};", f"ideal KT = std(KNOWN + ideal({targ}));", "ideal J; poly c; int w; int d;"]
    nonzero = inst.get("nonzero_variables") or []
    for k, cand in enumerate(batch):
        lines.append(f"c = {cand};")
        lines.append("if (size(reduce(c, KT)) != 0) {")
        lines.append("  J = std(KNOWN + ideal(c));")
        lines.append("  w = 1;")
        for j in range(1, len(inst["targets"]) + 1):
            lines.append(f"  if (size(reduce(q{j}, J)) != 0) {{ w = 0; }}")
        lines.append("  d = 0;")
        lines.append("  if (size(reduce(one, J)) == 0) { d = 1; }")
        for v in nonzero:
            lines.append(f"  if (size(reduce({v}, J)) == 0) {{ d = 1; }}")
        lines.append(f'  if ((w == 1) && (d == 0)) {{ print("OK {offset + k}"); }}')
        lines.append("}")
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def run_singular(script: str, timeout: float) -> str:
    with tempfile.TemporaryDirectory(prefix="enum_") as td:
        path = Path(td) / "job.sing"
        path.write_text(script)
        proc = subprocess.run([SINGULAR, "-q", "--random=1", str(path)], capture_output=True,
            stdin=subprocess.DEVNULL, text=True,
                              timeout=max(1.0, timeout), check=False)
    errors = [ln.strip() for ln in (proc.stdout + '\n' + proc.stderr).splitlines() if ln.strip().startswith('?')]
    if errors:
        raise RuntimeError('Singular error: ' + ' | '.join(errors[:4]))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:])
    return proc.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inst = json.loads(Path(args.instance).read_text())
    limit = float(os.environ.get("ABDUCTION_TIME_LIMIT", "60"))
    budget = min(float(os.environ.get("ENUM_BUDGET", "5")), max(1.0, limit - 6.0))
    max_candidates = int(os.environ.get("ENUM_MAX_CANDIDATES", "0"))
    end = time.monotonic() + budget
    names = inst["variables"]
    accepted: list[str] = []
    tested = 0
    gen = candidates(len(names), names)
    offset = 0
    try:
        while time.monotonic() < end and len(accepted) < MAX_ACCEPT:
            size = BATCH if not max_candidates else min(BATCH, max_candidates - tested)
            if size <= 0:
                break
            batch = list(itertools.islice(gen, size))
            if not batch:
                break
            try:
                out = run_singular(batch_script(inst, batch, offset), end - time.monotonic())
            except subprocess.TimeoutExpired:
                break
            tested += len(batch)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[0] == "OK":
                    accepted.append(batch[int(parts[1]) - offset])
            offset += len(batch)
    except Exception as exc:  # noqa: BLE001 - always emit a well-formed answer
        print(f"enumeration stopped: {exc}", file=sys.stderr)
    payload = {
        "method": "enumerative_baseline",
        "candidate_sets": [[c] for c in accepted[:MAX_ACCEPT]],
        "diagnostics": {"tested": tested, "budget_seconds": budget, "max_candidates": max_candidates},
    }
    Path(args.output).write_text(json.dumps(payload))


if __name__ == "__main__":
    main()
