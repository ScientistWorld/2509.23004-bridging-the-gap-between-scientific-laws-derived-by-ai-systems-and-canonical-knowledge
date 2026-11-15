#!/usr/bin/env python3
"""Visible train evaluator for polynomial abduction solvers.

The evaluator owns everything on the scoring side: the instances (built from
complete theories that exist only in ``eval/test``), the per-instance time
limit, the candidate budget, and the ground truth.  It runs every solver found
in ``scripts/solvers/*.sh`` on every instance:

    bash scripts/solvers/<name>.sh <instance.json> <output.json>

with ``ABDUCTION_TIME_LIMIT`` set, reads only the ranked list of candidate
polynomial sets from ``output.json`` and recomputes every scored quantity in
Singular.  Nothing a solver reports about itself (flags, scores, problem
definitions) is read.

Per candidate set S (only the first TOP_K sets count):
  derives     every target lies in the ideal <known axioms, S>
  sound       every polynomial of S vanishes on every solution of the complete
              theory at which the instance's nonzero quantities are nonzero
              (radical membership in the complete theory saturated by their
              product), so contradictions, zero-forcing and false laws are
              rejected while true laws that need a physical quantity to be
              nonzero (for example after dividing by it) are accepted
  nontrivial  no polynomial of S already lies in <known axioms, targets,
              targets with their monomial factors in nonzero quantities
              divided out>, so restatements of the target earn nothing
  valid       derives and sound and nontrivial
  recovered   valid, and every removed axiom lies in <known, S> saturated by
              the instance's nonzero variables (equivalent to the complete
              theory wherever physical quantities are nonzero)
  axioms      for a valid set, the number of removed axioms it recovers in that
              sense (partial recovery, multiple-consequence experiment)
A run that crashes, times out or writes malformed output fails the instance,
which then receives the worst value of every scored metric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from polyutil import Poly, PolyError, parse_poly  # noqa: E402

SLICE = "train"
DEFAULT_INSTANCES = HERE / "instances.json"
DEFAULT_OUTPUT = ROOT / "scoring" / "scores_train.json"
DEFAULT_SOLVERS_DIR = ROOT / "scripts" / "solvers"
TIME_LIMIT_SECONDS = 60
GRACE_SECONDS = 5
TOP_K = 5
EVAL_TIMEOUT_SECONDS = 300
MAX_OUTPUT_BYTES = 2_000_000
CANDIDATE_LIMITS = {"max_chars": 4000, "max_terms": 400, "max_degree": 24, "max_exponent": 12, "max_int_digits": 60}
TARGET_LIMITS = {"max_terms": 5000, "max_degree": 80, "max_exponent": 80, "max_chars": 100000, "max_int_digits": 200}
SOLVER_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


def resolve_singular() -> str:
    """Absolute path of the Singular binary, fixed before any solver runs."""
    found = shutil.which(os.environ.get("SINGULAR_BIN", "Singular"))
    if not found:
        raise SystemExit("Singular not found on PATH")
    path = Path(found).resolve()
    if ROOT in path.parents:
        raise SystemExit(f"refusing a Singular binary inside the workspace: {path}")
    return str(path)


SINGULAR = ""  # resolved in evaluate(), before the first solver runs

EXPERIMENTS_BY_SIZE = {
    1: "single_missing_axiom",
    2: "two_missing_axioms",
    3: "three_missing_axioms",
}
MC_EXPERIMENT = "multiple_consequences"
EXPERIMENTS = list(EXPERIMENTS_BY_SIZE.values()) + [MC_EXPERIMENT]


def experiment_of(inst: dict) -> str:
    """Experiment an instance belongs to (fixed by the instance file)."""
    return inst.get("experiment") or EXPERIMENTS_BY_SIZE[inst["num_missing"]]


# --------------------------------------------------------------------------
# instances and solvers
# --------------------------------------------------------------------------

def load_instances(path: Path) -> list[dict]:
    if not path.is_file():
        import build_instances  # same-slice builder

        build_instances.build(path, timeout=900.0)
    payload = json.loads(path.read_text())
    return payload["instances"]


def discover_solvers(solvers_dir: Path) -> list[tuple[str, Path]]:
    found = []
    for path in sorted(solvers_dir.resolve().glob("*.sh")):
        if SOLVER_NAME_RE.match(path.stem):
            found.append((path.stem, path))
    return found


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def run_solver(solver: Path, public: dict, time_limit: float) -> tuple[str, object, float, str]:
    with tempfile.TemporaryDirectory(prefix="abduction_") as td:
        inp = Path(td) / "instance.json"
        out = Path(td) / "output.json"
        payload = dict(public)
        payload["time_limit_seconds"] = time_limit
        inp.write_text(json.dumps(payload))
        env = dict(os.environ)
        env["ABDUCTION_TIME_LIMIT"] = str(time_limit)
        start = time.monotonic()
        with open(Path(td) / "solver.log", "w") as log:
            proc = subprocess.Popen(
                ["bash", str(solver), str(inp), str(out)],
                cwd=str(ROOT),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            try:
                rc = proc.wait(timeout=time_limit + GRACE_SECONDS)
                status = "ok" if rc == 0 else f"exit_{rc}"
            except subprocess.TimeoutExpired:
                status = "timeout"
            finally:
                kill_group(proc)
        elapsed = time.monotonic() - start
        try:
            tail = (Path(td) / "solver.log").read_text(errors="replace")[-600:]
        except OSError:
            tail = ""
        if status != "ok":
            return status, None, elapsed, tail
        if not out.is_file():
            return "missing_output", None, elapsed, tail
        if out.stat().st_size > MAX_OUTPUT_BYTES:
            return "output_too_large", None, elapsed, tail
        try:
            data = json.loads(out.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "invalid_json", None, elapsed, tail
    return "ok", data, elapsed, tail


def canonical_set(entry, public: dict):
    """Return canonical polynomial strings of a well-formed set, else None."""
    if not isinstance(entry, list) or not (1 <= len(entry) <= public["num_missing"]):
        return None
    polys: list[str] = []
    for text in entry:
        try:
            poly = parse_poly(text, public["variables"], CANDIDATE_LIMITS)
        except (PolyError, RecursionError):
            return None
        if poly.is_zero():
            return None
        canon = poly.to_string(public["variables"])
        if canon not in polys:
            polys.append(canon)
    return polys


def extract_sets(data, public: dict):
    if not isinstance(data, dict):
        return None
    sets = data.get("candidate_sets")
    if not isinstance(sets, list):
        return None
    return [canonical_set(entry, public) for entry in sets[:TOP_K]]


# --------------------------------------------------------------------------
# Singular scoring
# --------------------------------------------------------------------------

def run_singular(script: str, timeout: float) -> str:
    with tempfile.TemporaryDirectory(prefix="abduction_eval_") as td:
        path = Path(td) / "score.sing"
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
        raise RuntimeError(f"Singular exit {proc.returncode}: {proc.stderr[-1000:]}")
    return proc.stdout


def strip_nonzero_content(expr: str, names: list[str], nonzero: list[str]) -> str:
    """Divide a polynomial by its largest monomial factor in nonzero variables."""
    poly = parse_poly(expr, names, TARGET_LIMITS)
    nz = {names.index(v) for v in nonzero if v in names}
    mins = [min(e[i] for e in poly.terms) if i in nz else 0 for i in range(poly.nvars)]
    terms = {tuple(a - b for a, b in zip(e, mins)): c for e, c in poly.terms.items()}
    return Poly(poly.nvars, terms).to_string(names)


def scoring_script(inst: dict, sets: list) -> str:
    public, hidden = inst["public"], inst["hidden"]
    nonzero = public["nonzero_variables"]
    hnz = "*".join(nonzero) if nonzero else "1"
    lines = [
        f"ring R = 0, (t, {', '.join(public['variables'])}), dp;",
        "short = 0;",
        "poly one = 1;",
        f"poly hnz = {hnz};",
        "int der; int ntr; int rec; int nrec;",
        "ideal G; ideal JK; ideal JS;",
    ]
    for i, a in enumerate(hidden["full_axioms"], 1):
        lines.append(f"poly a{i} = {a};")
    lines.append("ideal FULL = " + ", ".join(f"a{i}" for i in range(1, len(hidden["full_axioms"]) + 1)) + ";")
    # Soundness is judged on the complete theory away from the locus where a
    # nonzero quantity vanishes: u is sound iff u*hnz lies in the radical of
    # FULL, i.e. u lies in the radical of FULL saturated by hnz (SATF).
    saturated = hidden.get("full_saturated")
    if saturated:
        lines.append("ideal SATF = " + ", ".join(saturated) + ";")
        lines.append("ideal SFS = std(SATF);")
        rabinowitsch = "std(SATF + ideal(1 - t*{u}))"
    else:
        lines.append("ideal SFS = std(FULL);")
        rabinowitsch = "std(FULL + ideal(1 - t*hnz*{u}))"
    known = public["known_axioms"]
    for i, a in enumerate(known, 1):
        lines.append(f"poly k{i} = {a};")
    lines.append("ideal KNOWN = " + (", ".join(f"k{i}" for i in range(1, len(known) + 1)) or "0") + ";")
    for j, q in enumerate(public["targets"], 1):
        lines.append(f"poly q{j} = {q};")
    stripped = [strip_nonzero_content(q, public["variables"], nonzero) for q in public["targets"]]
    lines.append("ideal KT = std(KNOWN + ideal(" + ", ".join(f"q{j}" for j in range(1, len(public["targets"]) + 1))
                 + ") + ideal(" + ", ".join(stripped) + "));")
    for i, r in enumerate(hidden["removed_axioms"], 1):
        lines.append(f"poly r{i} = {r};")

    names: dict[str, str] = {}
    for s in sets:
        for p in s or []:
            if p not in names:
                u = f"u{len(names) + 1}"
                names[p] = u
                lines += [
                    f"poly {u} = {p};",
                    f"int s{u} = 0;",
                    f"if (size(reduce({u}, SFS)) == 0) {{ s{u} = 1; }} else {{ G = {rabinowitsch.format(u=u)}; "
                    f"if (size(reduce(one, G)) == 0) {{ s{u} = 1; }} }}",
                    f'print("POLY {u} " + string(s{u}));',
                ]
    nq = len(public["targets"])
    nr = len(hidden["removed_axioms"])
    for k, s in enumerate(sets):
        if not s:
            continue
        us = [names[p] for p in s]
        ideal_s = "ideal(" + ", ".join(us) + ")"
        lines.append(f"JK = std(KNOWN + {ideal_s});")
        lines.append("der = 1;")
        for j in range(1, nq + 1):
            lines.append(f"if (size(reduce(q{j}, JK)) != 0) {{ der = 0; }}")
        lines.append("ntr = 1;")
        for u in us:
            lines.append(f"if (size(reduce({u}, KT)) == 0) {{ ntr = 0; }}")
        sound_all = " && ".join(f"(s{u} == 1)" for u in us)
        miss = " || ".join(f"(size(reduce(r{i}, JK)) != 0)" for i in range(1, nr + 1))
        lines.append("rec = 0; nrec = 0;")
        lines.append(f"if ((der == 1) && (ntr == 1) && {sound_all}) {{")
        lines.append(f"  nrec = {nr};")
        lines.append(f"  if ({miss}) {{")
        lines.append(f"    JS = std(KNOWN + {ideal_s} + ideal(1 - t*hnz));")
        lines.append("    nrec = 0;")
        for i in range(1, nr + 1):
            lines.append(f"    if (size(reduce(r{i}, JS)) == 0) {{ nrec = nrec + 1; }}")
        lines.append("  }")
        lines.append(f"  if (nrec == {nr}) {{ rec = 1; }}")
        lines.append("}")
        lines.append(f'print("SET {k} " + string(der) + " " + string(ntr) + " " + string(rec) + " " + string(nrec));')
    lines.append("quit;")
    return "\n".join(lines) + "\n"


def score_sets(inst: dict, sets: list) -> tuple[list, str | None]:
    """Return per-set verdict dicts (None for malformed sets) and an error note."""
    verdicts: list = [None] * len(sets)
    if not any(sets):
        return verdicts, None
    try:
        out = run_singular(scoring_script(inst, sets), EVAL_TIMEOUT_SECONDS)
    except (subprocess.TimeoutExpired, RuntimeError) as exc:
        return verdicts, f"scoring_failed: {type(exc).__name__}: {str(exc)[:400]}"
    sound: dict[str, bool] = {}
    flags: dict[int, tuple[bool, bool, bool, int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "POLY":
            sound[parts[1]] = parts[2] == "1"
        elif len(parts) == 6 and parts[0] == "SET":
            flags[int(parts[1])] = (parts[2] == "1", parts[3] == "1", parts[4] == "1", int(parts[5]))
    names: dict[str, str] = {}
    for s in sets:
        for p in s or []:
            names.setdefault(p, f"u{len(names) + 1}")
    error = None
    for k, s in enumerate(sets):
        if not s:
            continue
        if k not in flags or any(names[p] not in sound for p in s):
            error = "scoring_incomplete"
            continue
        der, ntr, rec, nrec = flags[k]
        snd = all(sound[names[p]] for p in s)
        valid = der and snd and ntr
        verdicts[k] = {
            "derives": der,
            "sound": snd,
            "nontrivial": ntr,
            "valid": valid,
            "unsound": der and not snd,
            "recovered": valid and rec,
            "axioms_recovered": nrec if valid else 0,
        }
    return verdicts, error


def evaluate_instance(inst: dict, status: str, data) -> dict:
    record = {"id": inst["id"], "experiment": experiment_of(inst), "num_missing": inst["num_missing"],
              "status": status}
    sets = extract_sets(data, inst["public"]) if status == "ok" else None
    if sets is None:
        record.update({"failed": True, "status": status if status != "ok" else "invalid_output"})
        return record
    verdicts, error = score_sets(inst, sets)
    record.update({"failed": False, "num_sets": len(sets), "verdicts": verdicts})
    if error:
        record["scoring_error"] = error
    return record


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------

def instance_outcome(record: dict) -> dict:
    if record["failed"]:
        return {"failed": 1, "recovered": 0, "valid": 0, "axiom_fraction": 0.0, "unsound": 1, "top1_recovered": 0,
                "top1_valid": 0, "sets": 0}
    v = [x for x in record["verdicts"]]
    first = v[0] if v else None
    return {
        "failed": 0,
        "recovered": int(any(x and x["recovered"] for x in v)),
        "valid": int(any(x and x["valid"] for x in v)),
        "axiom_fraction": max([x.get("axioms_recovered", 0) for x in v if x] + [0]) / max(1, record["num_missing"]),
        # sets the evaluator could not verify count against the constraint
        "unsound": int(any(x and x["unsound"] for x in v) or bool(record.get("scoring_error"))),
        "top1_recovered": int(bool(first and first["recovered"])),
        "top1_valid": int(bool(first and first["valid"])),
        "sets": record["num_sets"],
    }


def aggregate(records: list[dict], experiment: str, total: int) -> dict:
    outs = [instance_outcome(r) for r in records if r["experiment"] == experiment]
    n = total
    def rate(key: str) -> float:
        return sum(o[key] for o in outs) / n if n else 0.0
    # Recovery is the goal of the single-axiom and multiple-consequence experiments;
    # with one observed law and several missing axioms only an explanation is.
    top1_key = "top1_recovered" if experiment in ("single_missing_axiom", MC_EXPERIMENT) else "top1_valid"
    row = {
        "recovery_rate": rate("recovered"),
        "explanation_rate": rate("valid"),
        "top1_success_rate": rate(top1_key),
        "unsound_rate": (sum(o["unsound"] for o in outs) + (n - len(outs))) / n if n else 1.0,
        "failed_rate": (sum(o["failed"] for o in outs) + (n - len(outs))) / n if n else 1.0,
        "mean_candidate_sets": sum(o["sets"] for o in outs) / n if n else 0.0,
        "instances": n,
    }
    if experiment == MC_EXPERIMENT:
        row["axiom_recovery_rate"] = rate("axiom_fraction")
    return row


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def solver_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def evaluate(args) -> dict:
    global SINGULAR
    SINGULAR = resolve_singular()
    instances = load_instances(Path(args.instances))
    if args.experiments:
        instances = [i for i in instances if experiment_of(i) in set(args.experiments)]
    if args.max_instances:
        kept, seen = [], {}
        for inst in instances:
            exp = experiment_of(inst)
            seen[exp] = seen.get(exp, 0) + 1
            if seen[exp] <= args.max_instances:
                kept.append(inst)
        instances = kept
    totals = {exp: sum(1 for i in instances if experiment_of(i) == exp) for exp in EXPERIMENTS}
    solvers = discover_solvers(Path(args.solvers_dir))
    if args.only:
        solvers = [(n, p) for n, p in solvers if n in set(args.only)]
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    scores = {
        "slice": SLICE,
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "top_k": TOP_K,
        "experiments": {name: {"results": {}} for name in EXPERIMENTS},
    }
    details: dict = {}
    for name, path in solvers:
        records = []
        started = time.monotonic()
        digest = solver_digest(path)
        for idx, inst in enumerate(instances, 1):
            cached = None
            cache_file = None
            if cache_dir is not None:
                cache_file = cache_dir / name / f"{digest}_{inst['id']}.json"
                if cache_file.is_file():
                    cached = json.loads(cache_file.read_text())
            if cached is not None:
                status, data, elapsed, tail = cached["status"], cached["data"], cached["elapsed"], cached["tail"]
            else:
                status, data, elapsed, tail = run_solver(path, inst["public"], TIME_LIMIT_SECONDS)
                if cache_file is not None:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps({"status": status, "data": data, "elapsed": elapsed, "tail": tail}))
            record = evaluate_instance(inst, status, data)
            record["solver_seconds"] = round(elapsed, 2)
            if args.details_out:
                if status != "ok":
                    record["log_tail"] = tail
                if isinstance(data, dict) and isinstance(data.get("diagnostics"), dict):
                    record["solver_diagnostics"] = json.dumps(data["diagnostics"])[:1500]
            records.append(record)
            out = instance_outcome(record)
            print(
                f"[eval {SLICE}] {name} {idx}/{len(instances)} {inst['id']} status={record['status']} "
                f"rec={out['recovered']} valid={out['valid']} unsound={out['unsound']} t={elapsed:.1f}s",
                flush=True,
            )
        for exp in EXPERIMENTS:
            scores["experiments"][exp]["results"][name] = aggregate(records, exp, totals[exp])
        details[name] = {"records": records, "seconds": round(time.monotonic() - started, 1)}
        print(f"[eval {SLICE}] {name} done in {details[name]['seconds']}s", flush=True)
    if args.details_out:
        Path(args.details_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.details_out).write_text(json.dumps(details, indent=1))
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", default=str(DEFAULT_INSTANCES))
    parser.add_argument("--solvers-dir", default=str(DEFAULT_SOLVERS_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--only", nargs="*", help="evaluate only these solver names (merged into --output)")
    parser.add_argument("--max-instances", type=int, default=0, help="smoke test: first N per experiment")
    parser.add_argument("--experiments", nargs="*", help="development: only instances of these experiments")
    parser.add_argument("--cache-dir", default="", help="optional resumable cache of solver outputs")
    parser.add_argument("--details-out", default="", help="optional per-instance verdict dump")
    args = parser.parse_args()
    scores = evaluate(args)
    out = Path(args.output)
    if args.only and out.is_file():
        # Partial re-evaluation: keep earlier rows of solvers that still exist.
        on_disk = {n for n, _p in discover_solvers(Path(args.solvers_dir))}
        previous = json.loads(out.read_text())
        for exp, block in previous.get("experiments", {}).items():
            for name, row in block.get("results", {}).items():
                if name in on_disk and name not in set(args.only) and exp in scores["experiments"]:
                    scores["experiments"][exp]["results"].setdefault(name, row)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(scores, indent=2, sort_keys=True))
    tmp.replace(out)
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
