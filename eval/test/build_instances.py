#!/usr/bin/env python3
"""Build the held-out abduction instances for the test slice.

Every instance comes from a complete polynomial theory stored only in
``eval/test/systems``.  Variables are renamed ``x1..xn`` and rescaled by fixed
rational unit factors; one, two or three axioms are removed.  The public part of
an instance is what a solver sees; the hidden part (removed axioms and the
complete theory) never leaves this directory.

Each instance is checked in Singular before it is kept:
  * every target lies in the ideal of the complete theory;
  * some target does not follow from the remaining (known) axioms, not even
    wherever the nonzero quantities are nonzero (ideal of the known axioms
    saturated by their product);
  * no removed axiom already lies in the ideal of known axioms + targets, where
    the targets are also taken with their monomial factors in nonzero
    quantities divided out (the evaluator's nontriviality test).

The hidden part also stores a Groebner basis of the complete theory saturated
by the product of the nonzero quantities (``full_saturated``): the evaluator's
soundness test asks whether a proposed law holds on every solution of the
complete theory at which those quantities are nonzero.

Multiple-consequence instances (experiment ``multiple_consequences``)
----------------------------------------------------------------------
Two, three or four axioms are removed and the solver receives several observed
laws: the theory's own target(s) plus laws that an experiment measuring one more
hidden quantity would observe.  Such a law is the simplest element involving
that quantity of the elimination ideal of the complete theory onto the measured
quantities plus it (divided by its nonzero monomial factor when the result is
still in the ideal).  For a removal of r axioms the instance carries r observed
laws in total (at least two); extra laws are drawn, in a seeded order, from those
that do not follow from the remaining axioms wherever the nonzero quantities are
nonzero.  A removal is kept when
  * every removed axiom is needed: for each removed axiom some observed law does
    not follow (wherever the nonzero quantities are nonzero) from the complete
    theory without that axiom;
  * no removed axiom lies in <known axioms, observed laws, observed laws divided
    by their nonzero monomial factors> (the evaluator's nontriviality test).
Whether each removed axiom follows from the known axioms and the observed laws
wherever the nonzero quantities are nonzero is recorded in the hidden part
(``identified``) as a diagnostic.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from polyutil import Poly, parse_poly  # noqa: E402

SLICE = "test"
SYSTEMS_DIR = HERE / "systems"
DEFAULT_OUTPUT = HERE / "instances.json"
SEED = "ai-noether-abduction-test-v1"
ID_PREFIX = "T"
MULTI_QUOTA = {2: 4, 3: 3}
MC_EXPERIMENT = "multiple_consequences"
MC_QUOTA = {2: 3, 3: 3, 4: 2}
MC_TRIES = 4
MC_MAX_TERMS = 30
MC_MAX_DEGREE = 12
SCALES = [Fraction(1), Fraction(2), Fraction(3), Fraction(1, 2), Fraction(1, 3), Fraction(3, 2), Fraction(2, 3)]
SYSTEM_LIMITS = {"max_terms": 5000, "max_degree": 60, "max_exponent": 40, "max_chars": 100000}
SAT_LIMITS = {"max_terms": 50000, "max_degree": 200, "max_exponent": 200, "max_chars": 5000000, "max_int_digits": 5000}
SINGULAR = os.environ.get("SINGULAR_BIN", "Singular")


def parse_system_file(path: Path) -> dict:
    text = path.read_text()
    vars_m = re.search(r"Variables:\s*\[(.*?)\]", text, re.S)
    eqs_m = re.search(r"Equations?:\s*(.*?)(?=\n\s*\n\s*Measured)", text, re.S | re.I)
    meas_m = re.search(r"Measured Variables:\s*\[(.*?)\]", text, re.S | re.I)
    targ_m = re.search(r"Target Polynomial:?\s*(.*)$", text, re.S | re.I)
    if not (vars_m and eqs_m and meas_m and targ_m):
        raise ValueError(f"cannot parse {path}")

    def names(blob: str) -> list[str]:
        return [v.strip().strip('"').strip("'") for v in blob.split(",") if v.strip()]

    return {
        "variables": names(vars_m.group(1)),
        "equations": [ln.strip() for ln in eqs_m.group(1).splitlines() if ln.strip()],
        "measured": names(meas_m.group(1)),
        "targets": [ln.strip() for ln in targ_m.group(1).splitlines() if ln.strip()],
    }


def disguise(system: dict, rng: random.Random) -> dict:
    """Rename variables to x1..xn and rescale each by a fixed rational unit."""
    orig = system["variables"]
    anon = [f"x{i + 1}" for i in range(len(orig))]
    scales = [rng.choice(SCALES) for _ in orig]

    def convert(expr: str) -> str:
        poly = parse_poly(expr, orig, SYSTEM_LIMITS)
        if poly.is_zero():
            raise ValueError(f"zero polynomial in system: {expr}")
        return poly.substitute_scaled(scales).to_string(anon)

    rename = dict(zip(orig, anon))
    return {
        "variables": anon,
        "axioms": [convert(e) for e in system["equations"]],
        "targets": [convert(t) for t in system["targets"]],
        "measured": [rename[v] for v in system["measured"] if v in rename],
    }


def run_singular(script: str, timeout: float) -> str:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "job.sing"
        path.write_text(script)
        proc = subprocess.run(
            [SINGULAR, "-q", "--random=1", str(path)],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
        )
    errors = [ln.strip() for ln in (proc.stdout + '\n' + proc.stderr).splitlines() if ln.strip().startswith('?')]
    if errors:
        raise RuntimeError('Singular error: ' + ' | '.join(errors[:4]))
    if proc.returncode != 0:
        raise RuntimeError(f"Singular failed ({proc.returncode}): {proc.stderr[-2000:]}")
    return proc.stdout


def tagged(output: str, tag: str) -> list[list[str]]:
    rows = []
    for line in output.splitlines():
        parts = line.strip().split()
        if parts and parts[0] == tag:
            rows.append(parts[1:])
    return rows


def strip_nonzero_content(expr: str, names: list[str], nonzero: list[str]) -> str:
    """Divide a polynomial by its largest monomial factor in nonzero variables."""
    poly = parse_poly(expr, names, SYSTEM_LIMITS)
    nz = {names.index(v) for v in nonzero}
    mins = [min(e[i] for e in poly.terms) if i in nz else 0 for i in range(poly.nvars)]
    if not any(mins):
        return poly.to_string(names)
    terms = {tuple(a - b for a, b in zip(e, mins)): c for e, c in poly.terms.items()}
    return Poly(poly.nvars, terms).to_string(names)


def preamble(sysd: dict, stripped: list[str] | None = None, nonzero: list[str] | None = None) -> list[str]:
    lines = [
        f"ring R = 0, (t, {', '.join(sysd['variables'])}), dp;",
        "short = 0;",
        "poly one = 1;",
        f"poly hnz = {'*'.join(nonzero) if nonzero else '1'};",
        "int ok; int wp; int nt; int ws;",
        "ideal G; ideal KN; ideal KS; ideal KTS; ideal KSS;",
    ]
    for i, a in enumerate(sysd["axioms"], 1):
        lines.append(f"poly a{i} = {a};")
    for j, q in enumerate(sysd["targets"], 1):
        lines.append(f"poly q{j} = {q};")
    lines.append("ideal FULL = " + ", ".join(f"a{i}" for i in range(1, len(sysd["axioms"]) + 1)) + ";")
    lines.append("ideal TARG = " + ", ".join(f"q{j}" for j in range(1, len(sysd["targets"]) + 1)) + ";")
    lines.append("ideal TARGS = " + ", ".join(stripped or sysd["targets"]) + ";")
    return lines


def removal_block(sysd: dict, key: int, removed: tuple[int, ...]) -> list[str]:
    known = [f"a{i + 1}" for i in range(len(sysd["axioms"])) if i not in removed]
    lines = [f"KN = {', '.join(known) if known else '0'};", "KS = std(KN);", "wp = 0;"]
    for j in range(1, len(sysd["targets"]) + 1):
        lines.append(f"if (size(reduce(q{j}, KS)) != 0) {{ wp = 1; }}")
    lines += ["KSS = std(KN + ideal(1 - t*hnz));", "ws = 0;"]
    for j in range(1, len(sysd["targets"]) + 1):
        lines.append(f"if (size(reduce(q{j}, KSS)) != 0) {{ ws = 1; }}")
    lines += ["KTS = std(KN + TARG + TARGS);", "nt = 1;"]
    for i in removed:
        lines.append(f"if (size(reduce(a{i + 1}, KTS)) == 0) {{ nt = 0; }}")
    lines.append(f'print("REM {key} " + string(wp) + " " + string(nt) + " " + string(ws));')
    return lines


def removal_flags(out: str) -> dict:
    """key -> (essential, nontrivial): essential = some target does not follow from
    the known axioms even away from the zero locus of the nonzero quantities."""
    return {int(r[0]): (r[1] == "1" and r[3] == "1", r[2] == "1") for r in tagged(out, "REM") if len(r) == 4}


def system_checks(sysd: dict, timeout: float) -> dict:
    lines = preamble(sysd)
    lines.append("ideal FS = std(FULL);")
    for j in range(1, len(sysd["targets"]) + 1):
        lines.append(f"ok = (size(reduce(q{j}, FS)) == 0);")
        lines.append(f'print("TGT {j} " + string(ok));')
    for i, v in enumerate(sysd["variables"], 1):
        lines.append(f"G = std(FULL + ideal(1 - t*{v}));")
        lines.append("ok = (size(reduce(one, G)) == 0);")
        lines.append(f'print("VAR {i} " + string(ok));')
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    targets_ok = all(r[1] == "1" for r in tagged(out, "TGT")) and len(tagged(out, "TGT")) == len(sysd["targets"])
    forced_zero = {int(r[0]) - 1 for r in tagged(out, "VAR") if r[1] == "1"}
    if len(tagged(out, "VAR")) != len(sysd["variables"]):
        raise RuntimeError("variable checks incomplete")
    return {"targets_ok": targets_ok, "forced_zero": forced_zero}


def single_checks(sysd: dict, stripped: list[str], nonzero: list[str], timeout: float) -> dict:
    lines = preamble(sysd, stripped, nonzero)
    for i in range(len(sysd["axioms"])):
        lines += removal_block(sysd, i, (i,))
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    singles = removal_flags(out)
    if set(singles) != set(range(len(sysd["axioms"]))):
        raise RuntimeError("single-removal checks incomplete")
    return singles


def saturated_basis(sysd: dict, nonzero: list[str], timeout: float) -> list[str]:
    """Reduced dp Groebner basis of FULL : (product of nonzero variables)^infinity."""
    variables = sysd["variables"]
    lines = preamble(sysd)
    hnz = "*".join(nonzero) if nonzero else "1"
    lines += [
        f"ideal SATF = eliminate(FULL + ideal(1 - t*{hnz}), t);",
        f"ring S = 0, ({', '.join(variables)}), dp;",
        "short = 0;",
        "option(redSB);",
        "ideal SG = std(imap(R, SATF));",
        "int si;",
        'for (si = 1; si <= ncols(SG); si++) { if (SG[si] != 0) { print("SAT " + string(SG[si])); } }',
        'print("SATDONE " + string(ncols(SG)));',
        "quit;",
    ]
    out = run_singular("\n".join(lines) + "\n", timeout)
    if not tagged(out, "SATDONE"):
        raise RuntimeError("saturation produced no output")
    gens = []
    for line in out.splitlines():
        if line.startswith("SAT "):
            gens.append(parse_poly(line[4:].strip(), variables, SAT_LIMITS).to_string(variables))
    if not gens:
        raise RuntimeError("empty saturation")
    return gens


def saturation_unit(sysd: dict, nonzero: list[str], timeout: float) -> bool:
    if not nonzero:
        return False
    lines = preamble(sysd)
    lines.append(f"G = std(FULL + ideal(1 - t*{'*'.join(nonzero)}));")
    lines.append("ok = (size(reduce(one, G)) == 0);")
    lines.append('print("SATUNIT " + string(ok));')
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    rows = tagged(out, "SATUNIT")
    if not rows:
        raise RuntimeError("saturation check produced no output")
    return rows[0][0] == "1"


def multi_checks(sysd: dict, stripped: list[str], nonzero: list[str], combos: list[tuple[int, ...]],
                 timeout: float) -> dict:
    if not combos:
        return {}
    lines = preamble(sysd, stripped, nonzero)
    for key, combo in enumerate(combos):
        lines += removal_block(sysd, key, combo)
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    return removal_flags(out)


def make_instance(name: str, sysd: dict, nonzero: list[str], removed: tuple[int, ...], saturated: list[str]) -> dict:
    digest = hashlib.sha256(f"{SEED}|{name}|{removed}".encode()).hexdigest()[:10]
    inst_id = f"{ID_PREFIX}{len(removed)}-{digest}"
    known = [a for i, a in enumerate(sysd["axioms"]) if i not in removed]
    public = {
        "id": inst_id,
        "num_missing": len(removed),
        "variables": sysd["variables"],
        "measured_variables": sysd["measured"],
        "nonzero_variables": nonzero,
        "known_axioms": known,
        "targets": sysd["targets"],
    }
    hidden = {
        "system": name,
        "removed_indices": [i + 1 for i in removed],
        "removed_axioms": [sysd["axioms"][i] for i in removed],
        "full_axioms": sysd["axioms"],
        "full_saturated": saturated,
    }
    return {"id": inst_id, "num_missing": len(removed), "public": public, "hidden": hidden}


# --------------------------------------------------------------------------
# multiple-consequence instances
# --------------------------------------------------------------------------

def _simplicity(poly: Poly, text: str) -> tuple:
    return (poly.num_terms(), poly.total_degree(), len(poly.used_variables()), len(text), text)


def consequence_pool(sysd: dict, nonzero: list[str], timeout: float) -> list[dict]:
    """One observed law per hidden quantity h: the simplest element involving h of
    the elimination ideal of the complete theory onto (measured variables + h)."""
    variables = sysd["variables"]
    measured = set(sysd["measured"])
    hidden = [v for v in variables if v not in measured]
    if not hidden:
        return []
    head = [f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;", "option(redSB);", "int gi;", "ideal E;"]
    for i, a in enumerate(sysd["axioms"], 1):
        head.append(f"poly a{i} = {a};")
    head.append("ideal FULL = " + ", ".join(f"a{i}" for i in range(1, len(sysd["axioms"]) + 1)) + ";")
    out = ""
    for idx, h in enumerate(hidden):
        keep = [v for v in variables if v in measured or v == h]
        elim = [v for v in hidden if v != h]
        lines = list(head)
        lines.append(f"E = eliminate(FULL, {'*'.join(elim)});" if elim else "E = FULL;")
        lines += [
            f"ring S = 0, ({', '.join(keep)}), dp;",
            "short = 0;",
            "option(redSB);",
            "ideal G = std(imap(R, E));",
            f"for (gi = 1; gi <= ncols(G); gi++) {{ if (G[gi] != 0) {{ print(\"ELIM {idx} \" + string(G[gi])); }} }}",
            "quit;",
        ]
        try:
            out += run_singular("\n".join(lines) + "\n", min(timeout, 120.0)) + "\n"
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print(f"[build] elimination for {h} skipped ({type(exc).__name__})", flush=True)
    best: dict[int, tuple] = {}
    for line in out.splitlines():
        parts = line.strip().split(" ", 2)
        if len(parts) != 3 or parts[0] != "ELIM":
            continue
        idx = int(parts[1])
        poly = parse_poly(parts[2], variables, SYSTEM_LIMITS)
        if variables.index(hidden[idx]) not in poly.used_variables():
            continue
        if poly.num_terms() > MC_MAX_TERMS or poly.total_degree() > MC_MAX_DEGREE:
            continue  # keep observed laws of moderate size
        text = poly.to_string(variables)
        key = _simplicity(poly, text)
        if idx not in best or key < best[idx][0]:
            best[idx] = (key, text)
    pool = []
    for idx in sorted(best):
        text = best[idx][1]
        stripped = strip_nonzero_content(text, variables, nonzero)
        pool.append({"source": hidden[idx], "poly": text, "stripped": stripped})
    # Prefer the law divided by its nonzero monomial factor when that is still in the ideal.
    todo = [p for p in pool if p["stripped"] != p["poly"]]
    if todo:
        lines = [f"ring R = 0, ({', '.join(variables)}), dp;", "short = 0;"]
        for i, a in enumerate(sysd["axioms"], 1):
            lines.append(f"poly a{i} = {a};")
        lines.append("ideal FS = std(ideal(" + ", ".join(f"a{i}" for i in range(1, len(sysd["axioms"]) + 1)) + "));")
        for k, p in enumerate(todo):
            lines.append(f'print("MEM {k} " + string(size(reduce({p["stripped"]}, FS)) == 0));')
        lines.append("quit;")
        out = run_singular("\n".join(lines) + "\n", timeout)
        member = {int(r[0]): r[1] == "1" for r in tagged(out, "MEM") if len(r) == 2}
        for k, p in enumerate(todo):
            if member.get(k):
                p["poly"] = p["stripped"]
    return [{"source": p["source"], "poly": p["poly"]} for p in pool]


def mc_flag_script(sysd: dict, nonzero: list[str], laws: list[str], probes: list[tuple[int, ...]]) -> str:
    """NEED i j: law j does not follow (generically) from the theory without axiom i.
    INF k j: law j does not follow (generically) from the known axioms of probe k."""
    lines = preamble(sysd, None, nonzero)
    for j, q in enumerate(laws):
        lines.append(f"poly c{j} = {q};")
    m = len(sysd["axioms"])
    for i in range(m):
        rest = [f"a{k + 1}" for k in range(m) if k != i]
        lines.append(f"G = std(ideal({', '.join(rest) if rest else '0'}) + ideal(1 - t*hnz));")
        for j in range(len(laws)):
            lines.append(f'print("NEED {i} {j} " + string(size(reduce(c{j}, G)) != 0));')
    for k, removed in enumerate(probes):
        known = [f"a{i + 1}" for i in range(m) if i not in removed]
        lines.append(f"G = std(ideal({', '.join(known) if known else '0'}) + ideal(1 - t*hnz));")
        for j in range(len(laws)):
            lines.append(f'print("INF {k} {j} " + string(size(reduce(c{j}, G)) != 0));')
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def mc_candidate_script(sysd: dict, nonzero: list[str], laws: list[str],
                        cands: list[tuple[tuple[int, ...], tuple[int, ...]]]) -> str:
    """CAND k nt id_1..id_r for (removed, chosen laws): nontriviality and generic identification."""
    variables = sysd["variables"]
    lines = preamble(sysd, None, nonzero)
    for j, q in enumerate(laws):
        lines.append(f"poly c{j} = {q};")
        lines.append(f"poly s{j} = {strip_nonzero_content(q, variables, nonzero)};")
    m = len(sysd["axioms"])
    for k, (removed, chosen) in enumerate(cands):
        known = [f"a{i + 1}" for i in range(m) if i not in removed]
        qs = ", ".join(f"c{j}" for j in chosen)
        ss = ", ".join(f"s{j}" for j in chosen)
        lines.append(f"KN = ideal({', '.join(known) if known else '0'});")
        lines.append(f"KTS = std(KN + ideal({qs}) + ideal({ss}));")
        lines.append(f"KS = std(KN + ideal({qs}) + ideal(1 - t*hnz));")
        lines.append("nt = 1;")
        for i in removed:
            lines.append(f"if (size(reduce(a{i + 1}, KTS)) == 0) {{ nt = 0; }}")
        ident = " + \" \" + ".join(f"string(size(reduce(a{i + 1}, KS)) == 0)" for i in removed)
        lines.append(f'print("CAND {k} " + string(nt) + " " + {ident});')
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def make_mc_instance(name: str, sysd: dict, nonzero: list[str], removed: tuple[int, ...],
                     laws: list[dict], chosen: tuple[int, ...], identified: list[bool],
                     saturated: list[str]) -> dict:
    variables = sysd["variables"]
    targets = [laws[j]["poly"] for j in chosen]
    sources = [laws[j]["source"] for j in chosen]
    digest = hashlib.sha256(f"{SEED}|mc|{name}|{removed}|{sources}".encode()).hexdigest()[:10]
    inst_id = f"{ID_PREFIX}C{len(removed)}-{digest}"
    used: set[int] = set()
    for q in targets:
        used |= parse_poly(q, variables, SYSTEM_LIMITS).used_variables()
    measured = list(sysd["measured"]) + [v for i, v in enumerate(variables)
                                         if i in used and v not in set(sysd["measured"])]
    public = {
        "id": inst_id,
        "num_missing": len(removed),
        "variables": variables,
        "measured_variables": measured,
        "nonzero_variables": nonzero,
        "known_axioms": [a for i, a in enumerate(sysd["axioms"]) if i not in removed],
        "targets": targets,
    }
    hidden = {
        "system": name,
        "removed_indices": [i + 1 for i in removed],
        "removed_axioms": [sysd["axioms"][i] for i in removed],
        "full_axioms": sysd["axioms"],
        "full_saturated": saturated,
        "consequence_sources": sources,
        "identified": identified,
    }
    return {"id": inst_id, "experiment": MC_EXPERIMENT, "num_missing": len(removed), "public": public, "hidden": hidden}


def build_mc(name: str, sysd: dict, nonzero: list[str], saturated: list[str], timeout: float) -> tuple[list[dict], dict]:
    """Multiple-consequence instances of one theory (see module docstring)."""
    rng = random.Random(f"{SEED}|mc|{name}")
    variables = sysd["variables"]
    pool = consequence_pool(sysd, nonzero, timeout)
    laws = [{"source": "target", "poly": q} for q in sysd["targets"]] + pool
    n_target = len(sysd["targets"])
    m = len(sysd["axioms"])
    probes: list[tuple[int, ...]] = []
    for size, quota in sorted(MC_QUOTA.items()):
        combos = [c for c in itertools.combinations(range(m), size) if m - size >= 1]
        rng.shuffle(combos)
        probes += combos[: 3 * quota + 4]
    if not probes or not pool:
        return [], {"pool": len(pool), "instances_by_missing": {}}
    out = run_singular(mc_flag_script(sysd, nonzero, [l["poly"] for l in laws], probes), timeout)
    need = {(int(r[0]), int(r[1])): r[2] == "1" for r in tagged(out, "NEED") if len(r) == 3}
    inf = {(int(r[0]), int(r[1])): r[2] == "1" for r in tagged(out, "INF") if len(r) == 3}
    if len(need) != m * len(laws) or len(inf) != len(probes) * len(laws):
        raise RuntimeError("multiple-consequence flags incomplete")
    cands: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    owner: list[int] = []
    for k, removed in enumerate(probes):
        size = len(removed)
        extra = max(1, max(size, 2) - n_target)
        informative = [j for j in range(n_target, len(laws)) if inf[(k, j)]]
        if len(informative) < extra:
            continue
        order = list(informative)
        random.Random(f"{SEED}|mc|{name}|{removed}").shuffle(order)
        seen: set[frozenset] = set()
        tries = 0
        for start in range(len(order)):
            pick = [order[(start + i) % len(order)] for i in range(extra)]
            key = frozenset(pick)
            if key in seen:
                continue
            seen.add(key)
            chosen = tuple(range(n_target)) + tuple(sorted(pick))
            if not any(inf[(k, j)] for j in chosen):
                continue
            if not all(any(need[(i, j)] for j in chosen) for i in removed):
                continue
            cands.append((removed, chosen))
            owner.append(k)
            tries += 1
            if tries >= MC_TRIES:
                break
    if not cands:
        return [], {"pool": len(pool), "instances_by_missing": {}}
    out = run_singular(mc_candidate_script(sysd, nonzero, [l["poly"] for l in laws], cands), timeout)
    flags = {int(r[0]): r[1:] for r in tagged(out, "CAND")}
    if len(flags) != len(cands):
        raise RuntimeError("multiple-consequence candidate checks incomplete")
    picked: dict[tuple[int, ...], tuple[tuple[int, ...], list[bool]]] = {}
    for c, (removed, chosen) in enumerate(cands):
        if removed in picked or flags[c][0] != "1":
            continue
        picked[removed] = (chosen, [x == "1" for x in flags[c][1:]])
    instances: list[dict] = []
    counts: dict[int, int] = {}
    for size, quota in sorted(MC_QUOTA.items()):
        for removed in [p for p in probes if len(p) == size]:
            if counts.get(size, 0) >= quota or removed not in picked:
                continue
            chosen, identified = picked[removed]
            instances.append(make_mc_instance(name, sysd, nonzero, removed, laws, chosen, identified, saturated))
            counts[size] = counts.get(size, 0) + 1
    return instances, {
        "pool": len(pool),
        "pool_sources": [p["source"] for p in pool],
        "instances_by_missing": counts,
        "identified_all": sum(1 for i in instances if all(i["hidden"]["identified"])),
    }


def build_mc_only(output: Path, timeout: float) -> dict:
    """Replace the multiple-consequence instances of an existing instance file,
    keeping every other instance byte-identical."""
    payload = json.loads(output.read_text())
    legacy = [i for i in payload["instances"] if i.get("experiment") != MC_EXPERIMENT]
    by_system: dict[str, dict] = {}
    for inst in legacy:
        by_system.setdefault(inst["hidden"]["system"], inst)
    added: list[dict] = []
    for name in sorted(by_system):
        ref = by_system[name]
        raw = parse_system_file(SYSTEMS_DIR / name / "system.txt")
        sysd = disguise(raw, random.Random(f"{SEED}|{name}"))
        if sysd["axioms"] != ref["hidden"]["full_axioms"]:
            raise RuntimeError(f"{name}: rebuilt theory differs from the stored one")
        nonzero = ref["public"]["nonzero_variables"]
        try:
            insts, info = build_mc(name, sysd, nonzero, ref["hidden"]["full_saturated"], timeout)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            insts, info = [], {"status": f"skipped: {type(exc).__name__}"}
        added += insts
        payload["systems"].setdefault(name, {})["multiple_consequences"] = info
        print(f"[build] {name}: multiple consequences {info.get('instances_by_missing')}", flush=True)
    payload["instances"] = legacy + added
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True))
    tmp.replace(output)
    print(f"[build] wrote {len(legacy)} + {len(added)} instances to {output}", flush=True)
    return payload


def build(output: Path, timeout: float, only: list[str] | None = None) -> dict:
    instances: list[dict] = []
    mc_instances: list[dict] = []
    summary: dict = {}
    for sys_dir in sorted(p for p in SYSTEMS_DIR.iterdir() if (p / "system.txt").is_file()):
        name = sys_dir.name
        if only and name not in only:
            continue
        rng = random.Random(f"{SEED}|{name}")
        raw = parse_system_file(sys_dir / "system.txt")
        sysd = disguise(raw, rng)
        try:
            checks = system_checks(sysd, timeout)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            summary[name] = {"status": f"skipped: {type(exc).__name__}"}
            print(f"[build] {name}: SKIPPED ({type(exc).__name__}: {str(exc)[:200]})", flush=True)
            continue
        if not checks["targets_ok"]:
            summary[name] = {"status": "rejected: target not derivable from complete theory"}
            print(f"[build] {name}: REJECTED (target not in ideal of complete theory)", flush=True)
            continue
        nonzero = [v for i, v in enumerate(sysd["variables"]) if i not in checks["forced_zero"]]
        try:
            sat_unit = saturation_unit(sysd, nonzero, timeout)
        except (RuntimeError, subprocess.TimeoutExpired):
            sat_unit = True
        if sat_unit:
            print(f"[build] {name}: nonzero saturation is the unit ideal; using no nonzero variables", flush=True)
            nonzero = []
        try:
            saturated = saturated_basis(sysd, nonzero, timeout)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            # The evaluator then tests soundness per polynomial (slower, same answer).
            saturated = []
            print(f"[build] {name}: saturation not precomputed ({type(exc).__name__}: {str(exc)[:200]})", flush=True)
        stripped = [strip_nonzero_content(q, sysd["variables"], nonzero) for q in sysd["targets"]]
        try:
            single_flags = single_checks(sysd, stripped, nonzero, timeout)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            summary[name] = {"status": f"skipped: {type(exc).__name__}"}
            print(f"[build] {name}: SKIPPED ({type(exc).__name__}: {str(exc)[:200]})", flush=True)
            continue
        singles = [i for i, (wp, nt) in sorted(single_flags.items()) if wp and nt]
        essential = [i for i, (wp, _nt) in sorted(single_flags.items()) if wp]
        chosen: list[tuple[int, ...]] = [(i,) for i in singles]
        counts = {1: len(singles)}
        for size, quota in sorted(MULTI_QUOTA.items()):
            combos = [c for c in itertools.combinations(essential, size) if len(sysd["axioms"]) - size >= 1]
            rng.shuffle(combos)
            probe = combos[: 3 * quota + 2]
            try:
                flags = multi_checks(sysd, stripped, nonzero, probe, timeout)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                print(f"[build] {name}: multi-axiom checks failed ({type(exc).__name__})", flush=True)
                flags = {}
            picked = [c for k, c in enumerate(probe) if flags.get(k, (False, False)) == (True, True)][:quota]
            chosen += picked
            counts[size] = len(picked)
        for removed in chosen:
            instances.append(make_instance(name, sysd, nonzero, removed, saturated))
        summary[name] = {
            "status": "ok",
            "num_variables": len(sysd["variables"]),
            "num_axioms": len(sysd["axioms"]),
            "num_nonzero_variables": len(nonzero),
            "essential_axioms": [i + 1 for i in essential],
            "trivial_single_removals": [i + 1 for i, (wp, nt) in sorted(single_flags.items()) if wp and not nt],
            "targets_with_nonzero_content": sum(1 for q, s in zip(sysd["targets"], stripped)
                                                if parse_poly(q, sysd["variables"], SYSTEM_LIMITS).to_string(sysd["variables"]) != s),
            "saturated_generators": len(saturated),
            "instances_by_missing": counts,
        }
        print(f"[build] {name}: {counts}", flush=True)
        if chosen:
            try:
                insts, info = build_mc(name, sysd, nonzero, saturated, timeout)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                insts, info = [], {"status": f"skipped: {type(exc).__name__}"}
            mc_instances += insts
            summary[name]["multiple_consequences"] = info
            print(f"[build] {name}: multiple consequences {info.get('instances_by_missing')}", flush=True)
    instances += mc_instances
    payload = {"slice": SLICE, "seed": SEED, "systems": summary, "instances": instances}
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True))
    tmp.replace(output)
    print(f"[build] wrote {len(instances)} instances to {output}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--mc-only", action="store_true",
                        help="rebuild only the multiple-consequence instances of an existing file")
    args = parser.parse_args()
    if args.mc_only:
        build_mc_only(Path(args.output), args.timeout)
    else:
        build(Path(args.output), args.timeout, args.only)


if __name__ == "__main__":
    main()
