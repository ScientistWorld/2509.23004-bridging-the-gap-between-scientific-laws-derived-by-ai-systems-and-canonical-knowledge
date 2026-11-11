#!/usr/bin/env python3
"""Build the visible abduction instances for the train slice.

Every instance comes from one of the paper's twelve public benchmark theories
in ``data/systems_and_phenomena``.  Variables are renamed ``x1..xn`` and
rescaled by fixed rational unit factors (the same presentation as the held-out
slice); one, two or three axioms are removed.  The public part of an instance
is what a solver sees; the removed axioms are visible here because the train
theories are public.

Each instance is checked in Singular before it is kept:
  * every target lies in the ideal of the complete theory;
  * no target lies in the ideal of the remaining (known) axioms;
  * no removed axiom already lies in the ideal of known axioms + targets.
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
from polyutil import parse_poly  # noqa: E402

SLICE = "train"
SYSTEMS_DIR = HERE.parents[1] / "data" / "systems_and_phenomena"
DEFAULT_OUTPUT = HERE / "instances.json"
SEED = "ai-noether-abduction-train-v1"
ID_PREFIX = "V"
MULTI_QUOTA = {2: 3, 3: 3}
SCALES = [Fraction(1), Fraction(2), Fraction(3), Fraction(1, 2), Fraction(1, 3), Fraction(3, 2), Fraction(2, 3)]
SYSTEM_LIMITS = {"max_terms": 5000, "max_degree": 60, "max_exponent": 40, "max_chars": 100000}
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


def preamble(sysd: dict) -> list[str]:
    lines = [
        f"ring R = 0, (t, {', '.join(sysd['variables'])}), dp;",
        "short = 0;",
        "poly one = 1;",
        "int ok; int wp; int nt;",
        "ideal G; ideal KN; ideal KS; ideal KTS;",
    ]
    for i, a in enumerate(sysd["axioms"], 1):
        lines.append(f"poly a{i} = {a};")
    for j, q in enumerate(sysd["targets"], 1):
        lines.append(f"poly q{j} = {q};")
    lines.append("ideal FULL = " + ", ".join(f"a{i}" for i in range(1, len(sysd["axioms"]) + 1)) + ";")
    lines.append("ideal TARG = " + ", ".join(f"q{j}" for j in range(1, len(sysd["targets"]) + 1)) + ";")
    return lines


def removal_block(sysd: dict, key: int, removed: tuple[int, ...]) -> list[str]:
    known = [f"a{i + 1}" for i in range(len(sysd["axioms"])) if i not in removed]
    lines = [f"KN = {', '.join(known) if known else '0'};", "KS = std(KN);", "wp = 0;"]
    for j in range(1, len(sysd["targets"]) + 1):
        lines.append(f"if (size(reduce(q{j}, KS)) != 0) {{ wp = 1; }}")
    lines += ["KTS = std(KN + TARG);", "nt = 1;"]
    for i in removed:
        lines.append(f"if (size(reduce(a{i + 1}, KTS)) == 0) {{ nt = 0; }}")
    lines.append(f'print("REM {key} " + string(wp) + " " + string(nt));')
    return lines


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
    for i in range(len(sysd["axioms"])):
        lines += removal_block(sysd, i, (i,))
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    targets_ok = all(r[1] == "1" for r in tagged(out, "TGT")) and len(tagged(out, "TGT")) == len(sysd["targets"])
    forced_zero = {int(r[0]) - 1 for r in tagged(out, "VAR") if r[1] == "1"}
    if len(tagged(out, "VAR")) != len(sysd["variables"]):
        raise RuntimeError("variable checks incomplete")
    singles = {int(r[0]): (r[1] == "1", r[2] == "1") for r in tagged(out, "REM")}
    if set(singles) != set(range(len(sysd["axioms"]))):
        raise RuntimeError("single-removal checks incomplete")
    return {"targets_ok": targets_ok, "forced_zero": forced_zero, "singles": singles}


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


def multi_checks(sysd: dict, combos: list[tuple[int, ...]], timeout: float) -> dict:
    if not combos:
        return {}
    lines = preamble(sysd)
    for key, combo in enumerate(combos):
        lines += removal_block(sysd, key, combo)
    lines.append("quit;")
    out = run_singular("\n".join(lines) + "\n", timeout)
    return {int(r[0]): (r[1] == "1", r[2] == "1") for r in tagged(out, "REM")}


def make_instance(name: str, sysd: dict, nonzero: list[str], removed: tuple[int, ...]) -> dict:
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
    }
    return {"id": inst_id, "num_missing": len(removed), "public": public, "hidden": hidden}


def build(output: Path, timeout: float, only: list[str] | None = None) -> dict:
    instances: list[dict] = []
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
        singles = [i for i, (wp, nt) in sorted(checks["singles"].items()) if wp and nt]
        essential = [i for i, (wp, _nt) in sorted(checks["singles"].items()) if wp]
        chosen: list[tuple[int, ...]] = [(i,) for i in singles]
        counts = {1: len(singles)}
        for size, quota in sorted(MULTI_QUOTA.items()):
            combos = [c for c in itertools.combinations(essential, size) if len(sysd["axioms"]) - size >= 1]
            rng.shuffle(combos)
            probe = combos[: 3 * quota + 2]
            try:
                flags = multi_checks(sysd, probe, timeout)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                print(f"[build] {name}: multi-axiom checks failed ({type(exc).__name__})", flush=True)
                flags = {}
            picked = [c for k, c in enumerate(probe) if flags.get(k, (False, False)) == (True, True)][:quota]
            chosen += picked
            counts[size] = len(picked)
        for removed in chosen:
            instances.append(make_instance(name, sysd, nonzero, removed))
        summary[name] = {
            "status": "ok",
            "num_variables": len(sysd["variables"]),
            "num_axioms": len(sysd["axioms"]),
            "num_nonzero_variables": len(nonzero),
            "essential_axioms": [i + 1 for i in essential],
            "instances_by_missing": counts,
        }
        print(f"[build] {name}: {counts}", flush=True)
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
    args = parser.parse_args()
    build(Path(args.output), args.timeout, args.only)


if __name__ == "__main__":
    main()
