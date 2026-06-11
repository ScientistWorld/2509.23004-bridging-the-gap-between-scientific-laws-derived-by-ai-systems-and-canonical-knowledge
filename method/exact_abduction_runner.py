#!/usr/bin/env python3
"""Run a compact exact AI-Noether reproduction on benchmark systems.

This wrapper keeps the paper's exact Encode-Decompose-Reason computation:
known axioms and targets are encoded as an ideal, Singular computes minimal
associated primes, component generators become candidate axioms, and SymPy
Groebner elimination checks whether candidates derive the target.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import sympy as sp


class CaseTimeoutError(TimeoutError):
    """Raised when a whole abduction case exceeds the configured time budget."""


def _case_timeout_handler(signum, frame):  # noqa: ANN001 - signal handler signature is fixed
    raise CaseTimeoutError("case timeout")


@dataclass
class Problem:
    name: str
    variables: list[str]
    equations: list[str]
    measured_vars: list[str]
    targets: list[str]


NONZERO_FACTORS = {
    # Physical Kepler benchmark branches with zero mass, zero distance, zero
    # period, or collocated bodies are degenerate explanations rather than
    # missing scientific laws. Appendix E.2 of the paper filters these cases.
    "kepler": ["m1", "m2", "d1", "d2", "p", "d1+d2"],
}


def read_problem(path: Path, name: str) -> Problem:
    text = path.read_text()
    vars_match = re.search(r"Variables:\s*\[(.*?)\]", text, re.S)
    eqs_match = re.search(r"Equations?:\s*(.*?)(?=\n\s*\n\s*Measured)", text, re.S | re.I)
    measured_match = re.search(r"Measured Variables:\s*\[(.*?)\]", text, re.S | re.I)
    target_match = re.search(r"Target Polynomial:?\s*(.*)$", text, re.S | re.I)
    if not (vars_match and eqs_match and measured_match and target_match):
        raise ValueError(f"Could not parse problem file {path}")
    variables = [v.strip().strip('"').strip("'") for v in vars_match.group(1).split(",") if v.strip()]
    equations = [ln.strip() for ln in eqs_match.group(1).splitlines() if ln.strip()]
    measured = [v.strip().strip('"').strip("'") for v in measured_match.group(1).split(",") if v.strip()]
    targets = [ln.strip() for ln in target_match.group(1).splitlines() if ln.strip()]
    return Problem(name=name, variables=variables, equations=equations, measured_vars=measured, targets=targets)


def singular_script(
    variables: list[str],
    axioms: list[str],
    targets: list[str],
    saturation_factors: list[str] | None = None,
) -> str:
    ax_defs = "\n".join(f"poly a{i + 1} = {p};" for i, p in enumerate(axioms))
    target_defs = "\n".join(f"poly q{i + 1} = {p};" for i, p in enumerate(targets))
    ax_ideal = ", ".join(f"a{i + 1}" for i in range(len(axioms))) or "0"
    target_ideal = ", ".join(f"q{i + 1}" for i in range(len(targets))) or "0"
    if saturation_factors:
        sat_defs = "\n".join(f"poly nz{i + 1} = {p};" for i, p in enumerate(saturation_factors))
        sat_poly = "*".join(f"nz{i + 1}" for i in range(len(saturation_factors)))
        decompose = f"""{sat_defs}
poly nonzero_product = {sat_poly};
ideal encoded = ii + targ;
ideal nonzero_ideal = nonzero_product;
ideal saturated = sat(encoded, nonzero_ideal)[1];
list M1 = minAss(saturated);"""
    else:
        decompose = "list M1 = minAss(ii + targ);"
    return f"""LIB \"primdec.lib\";
ring baseR = 0, ({','.join(variables)}), dp;
{ax_defs}
ideal ii = {ax_ideal};
{target_defs}
ideal targ = {target_ideal};
{decompose}
print(\"=== SINGULAR_DECOMPOSITION_OUTPUT ===\");
M1;
print(\"=== END_SINGULAR_DECOMPOSITION_OUTPUT ===\");
quit;
"""


def run_singular(
    variables: list[str],
    axioms: list[str],
    targets: list[str],
    singular_bin: str,
    timeout: int,
    work_dir: Path,
    saturation_factors: list[str] | None = None,
) -> tuple[list[list[str]], str]:
    work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".sing", dir=work_dir, delete=False) as f:
        f.write(singular_script(variables, axioms, targets, saturation_factors=saturation_factors))
        script_path = Path(f.name)
    proc = subprocess.run(
        [singular_bin, "-q", str(script_path)],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    raw = proc.stdout + "\n" + proc.stderr
    (work_dir / "decomposition_stdout.txt").write_text(raw)
    if proc.returncode != 0:
        raise RuntimeError(f"Singular failed with code {proc.returncode}: {proc.stderr[-1000:]}")
    return parse_singular(raw), raw


def parse_singular(output: str) -> list[list[str]]:
    components: list[list[str]] = []
    current: list[str] = []
    active = False
    for line in output.splitlines():
        if re.match(r"^\s*\[\d+\]:\s*$", line):
            if current:
                components.append(current)
            current = []
            active = True
            continue
        match = re.match(r"^\s*_\[\d+\]\s*=\s*(.+?)\s*$", line)
        if match and active:
            current.append(match.group(1).strip())
    if current:
        components.append(current)
    return components


def symbol_table(variables: list[str]) -> dict[str, sp.Symbol]:
    return {name: sp.Symbol(name) for name in variables}


def sympify_poly(poly: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    return sp.sympify(poly.replace("^", "**"), locals=symbols)


def normalize_expr(expr: sp.Expr) -> str:
    expr = sp.Poly(sp.expand(expr)).as_expr()
    return str(expr)


def poly_equal_up_to_scalar(a: sp.Expr, b: sp.Expr, variables: list[sp.Symbol]) -> bool:
    pa = sp.Poly(sp.expand(a), *variables)
    pb = sp.Poly(sp.expand(b), *variables)
    if pa.is_zero and pb.is_zero:
        return True
    da = pa.as_dict()
    db = pb.as_dict()
    if set(da) != set(db) or not da:
        return False
    key = next(iter(da))
    ratio = sp.simplify(da[key] / db[key])
    return all(sp.simplify(da[k] - ratio * db[k]) == 0 for k in da)


def vars_in_poly(poly: str, variables: list[str]) -> list[str]:
    found = []
    for v in sorted(variables, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(v)}(?![A-Za-z0-9_])", poly):
            found.append(v)
    return found


def candidate_touches_unmeasured(
    candidates: list[str],
    variables: list[str],
    measured_vars: list[str],
) -> bool:
    """Return True for coupled explanations that introduce hidden variables.

    Multi-axiom cases in the paper can be credited when the recovered relation
    is coupled rather than a literal copy of every missing axiom. Degenerate
    explanations such as setting a measured variable to zero should not count.
    """
    measured = set(measured_vars)
    for candidate in candidates:
        if set(vars_in_poly(candidate, variables)) - measured:
            return True
    return False


def implied_by_ideal(poly: str, generators: list[str], variables: list[str]) -> bool:
    if not generators:
        return False
    symbols = symbol_table(variables)
    order = [symbols[v] for v in variables]
    gb = sp.groebner([sympify_poly(p, symbols) for p in generators], *order, order="lex")
    return sp.expand(gb.reduce(sympify_poly(poly, symbols))[1]) == 0


def candidate_sets(
    components: list[list[str]],
    max_size: int,
    variables: list[str],
    remaining_axioms: list[str],
    targets: list[str],
) -> Iterable[list[str]]:
    seen: set[tuple[str, ...]] = set()
    known_generators = remaining_axioms + targets
    for component in components:
        usable = [
            g
            for g in component
            if g not in {"0", "1", "-1"} and not implied_by_ideal(g, known_generators, variables)
        ]
        for size in range(1, min(max_size, len(usable)) + 1):
            for subset in itertools.combinations(usable, size):
                key = tuple(sorted(subset))
                if key not in seen:
                    seen.add(key)
                    yield list(subset)


def groebner_derives(
    variables: list[str],
    measured_vars: list[str],
    remaining_axioms: list[str],
    candidates: list[str],
    target: str,
) -> tuple[bool, bool]:
    symbols = symbol_table(variables)
    measured = [symbols[v] for v in measured_vars if v in symbols]
    non_measured = [symbols[v] for v in variables if v not in measured_vars]
    order = non_measured + measured
    polynomials = [sympify_poly(p, symbols) for p in remaining_axioms + candidates]
    target_expr = sympify_poly(target, symbols)
    if not polynomials:
        return False, False
    gb = sp.groebner(polynomials, *order, order="lex")
    elim = [g for g in gb.polys if set(g.as_expr().free_symbols).issubset(set(measured))]
    if not elim:
        return False, False
    elim_exprs = [g.as_expr() for g in elim]
    gb_elim = sp.groebner(elim_exprs, *measured, order="lex")
    weak = sp.expand(gb_elim.reduce(target_expr)[1]) == 0
    strong = any(poly_equal_up_to_scalar(g, target_expr, measured) for g in elim_exprs)
    return bool(weak), bool(strong)


def canonical_recovered(
    variables: list[str],
    remaining_axioms: list[str],
    candidates: list[str],
    missing_axiom: str,
) -> bool:
    symbols = symbol_table(variables)
    order = [symbols[v] for v in variables]
    polynomials = [sympify_poly(p, symbols) for p in remaining_axioms + candidates]
    missing = sympify_poly(missing_axiom, symbols)
    if not polynomials:
        return False
    gb = sp.groebner(polynomials, *order, order="lex")
    return sp.expand(gb.reduce(missing)[1]) == 0


def implies_degenerate_branch(
    variables: list[str],
    remaining_axioms: list[str],
    candidates: list[str],
    nonzero_factors: list[str],
) -> bool:
    return any(implied_by_ideal(factor, remaining_axioms + candidates, variables) for factor in nonzero_factors)


def run_case(problem: Problem, removed_indices: tuple[int, ...], args: argparse.Namespace, output_dir: Path) -> dict:
    remaining = [a for i, a in enumerate(problem.equations) if i not in removed_indices]
    removed = [problem.equations[i] for i in removed_indices]
    case_name = "combo_" + "_".join(str(i + 1) for i in removed_indices)
    case_dir = output_dir / problem.name / f"{len(removed_indices)}_removed" / case_name
    start = time.time()
    previous_handler = None
    if args.timeout_case > 0:
        previous_handler = signal.signal(signal.SIGALRM, _case_timeout_handler)
        signal.alarm(args.timeout_case)
    try:
        nonzero_factors = (
            NONZERO_FACTORS.get(problem.name, [])
            if args.saturate_nondegenerate or args.filter_degenerate
            else []
        )
        saturation_factors = nonzero_factors if args.saturate_nondegenerate else []
        components, raw = run_singular(
            problem.variables,
            remaining,
            problem.targets,
            args.singular,
            args.timeout_decomposition,
            case_dir,
            saturation_factors=saturation_factors,
        )
        accepted = []
        max_size = args.max_candidate_size if args.max_candidate_size > 0 else len(removed_indices) + len(problem.targets)
        for cand in candidate_sets(
            components,
            max_size=max_size,
            variables=problem.variables,
            remaining_axioms=remaining,
            targets=problem.targets,
        ):
            weak_all = True
            strong_all = True
            for target in problem.targets:
                target_vars = vars_in_poly(target, problem.variables)
                measured_subset = [v for v in problem.measured_vars if v in target_vars]
                weak, strong = groebner_derives(problem.variables, measured_subset, remaining, cand, target)
                weak_all = weak_all and weak
                strong_all = strong_all and strong
            if weak_all:
                if nonzero_factors and implies_degenerate_branch(
                    problem.variables, remaining, cand, nonzero_factors
                ):
                    continue
                accepted.append(
                    {
                        "candidates": cand,
                        "strong": strong_all,
                        "coupled": candidate_touches_unmeasured(
                            cand, problem.variables, problem.measured_vars
                        ),
                        "canonical_recovered": all(
                            canonical_recovered(problem.variables, remaining, cand, ax) for ax in removed
                        ),
                    }
                )
        minimal = []
        for item in sorted(accepted, key=lambda x: len(x["candidates"])):
            item_set = set(item["candidates"])
            if not any(set(prev["candidates"]).issubset(item_set) for prev in minimal):
                minimal.append(item)
        return {
            "problem": problem.name,
            "variables": problem.variables,
            "measured_vars": problem.measured_vars,
            "targets": problem.targets,
            "remaining_axioms": remaining,
            "removed_indices": [i + 1 for i in removed_indices],
            "removed_axioms": removed,
            "nonzero_factors": nonzero_factors,
            "status": "ok",
            "num_components": len(components),
            "num_accepted": len(minimal),
            "accepted": minimal,
            "success": any(item["canonical_recovered"] for item in minimal),
            "coupled_success": any(item["coupled"] for item in minimal),
            "strong_success": any(item["canonical_recovered"] and item["strong"] for item in minimal),
            "runtime_seconds": round(time.time() - start, 3),
        }
    except Exception as exc:  # noqa: BLE001 - record failed case for evaluation
        return {
            "problem": problem.name,
            "variables": problem.variables,
            "measured_vars": problem.measured_vars,
            "targets": problem.targets,
            "remaining_axioms": remaining,
            "removed_indices": [i + 1 for i in removed_indices],
            "removed_axioms": removed,
            "nonzero_factors": (
                NONZERO_FACTORS.get(problem.name, [])
                if args.saturate_nondegenerate or args.filter_degenerate
                else []
            ),
            "status": "timeout" if isinstance(exc, CaseTimeoutError) else "error",
            "error": str(exc),
            "num_components": 0,
            "num_accepted": 0,
            "accepted": [],
            "success": False,
            "coupled_success": False,
            "strong_success": False,
            "runtime_seconds": round(time.time() - start, 3),
        }
    finally:
        if args.timeout_case > 0:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)


def parse_sizes(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ".." in part:
            lo, hi = [int(x) for x in part.split("..", 1)]
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def parse_axiom_limits(spec: str) -> dict[str, int]:
    limits: dict[str, int] = {}
    if not spec:
        return limits
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        name, value = part.split("=", 1)
        limits[name.strip()] = int(value)
    return limits


def write_payload(
    output_path: Path,
    args: argparse.Namespace,
    sizes: list[int],
    axiom_limits: dict[str, int],
    results: list[dict],
) -> None:
    payload = {
        "method": "ai_noether_exact",
        "algorithm": "encode_primary_decompose_reason",
        "problems": args.problems,
        "sizes": sizes,
        "axiom_limits": axiom_limits,
        "cases": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--systems-dir", default="method/AI-Noether/systems_and_phenomena")
    parser.add_argument("--problems", nargs="+", default=["simple_harmonic_oscillator", "kepler"])
    parser.add_argument("--sizes", default="1")
    parser.add_argument("--singular", default=os.environ.get("SINGULAR_BIN", "Singular"))
    parser.add_argument("--timeout-decomposition", type=int, default=900)
    parser.add_argument(
        "--timeout-case",
        type=int,
        default=0,
        help="Whole-case timeout in seconds, including decomposition and reasoning. 0 disables it.",
    )
    parser.add_argument("--max-candidate-size", type=int, default=-1)
    parser.add_argument(
        "--saturate-nondegenerate",
        action="store_true",
        help="Saturate supported benchmark ideals by known nonzero physical factors.",
    )
    parser.add_argument(
        "--filter-degenerate",
        action="store_true",
        help="Filter candidate explanations that imply known zero-factor physical degeneracies.",
    )
    parser.add_argument(
        "--axiom-limits",
        default="",
        help="Optional comma-separated problem=count limits for removal combinations, e.g. hall=7.",
    )
    parser.add_argument("--output", default="scoring/ai_noether_exact_outputs.json")
    args = parser.parse_args()

    systems_dir = Path(args.systems_dir)
    output_path = Path(args.output)
    run_dir = output_path.with_suffix("")
    sizes = parse_sizes(args.sizes)
    axiom_limits = parse_axiom_limits(args.axiom_limits)
    results = []
    scheduled = []
    for name in args.problems:
        problem = read_problem(systems_dir / name / "system.txt", name)
        removal_count = min(len(problem.equations), axiom_limits.get(name, len(problem.equations)))
        for size in sizes:
            for combo in itertools.combinations(range(removal_count), size):
                scheduled.append((problem, combo))

    for idx, (problem, combo) in enumerate(scheduled, start=1):
        removed = ",".join(str(i + 1) for i in combo)
        print(f"[{idx}/{len(scheduled)}] {problem.name}: removing axiom(s) {removed}", flush=True)
        case = run_case(problem, combo, args, run_dir)
        results.append(case)
        print(
            f"[{idx}/{len(scheduled)}] {problem.name}: status={case['status']} "
            f"success={case['success']} accepted={case['num_accepted']} "
            f"runtime={case['runtime_seconds']}s",
            flush=True,
        )
        write_payload(output_path, args, sizes, axiom_limits, results)

    print(f"Wrote {output_path} with {len(results)} cases")


if __name__ == "__main__":
    main()
