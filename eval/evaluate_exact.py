#!/usr/bin/env python3
"""Evaluate AI-Noether exact abduction outputs without importing method code."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    import sympy as sp
except ModuleNotFoundError:  # pragma: no cover - login-node compatibility path
    sp = None


def symbol_table(variables: list[str]) -> dict[str, sp.Symbol]:
    if sp is None:
        raise RuntimeError("SymPy is required to recompute symbolic evaluation metrics.")
    return {name: sp.Symbol(name) for name in variables}


def sympify_poly(poly: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    return sp.sympify(poly.replace("^", "**"), locals=symbols)


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
    for variable in sorted(variables, key=len, reverse=True):
        left_ok = f"(?<![A-Za-z0-9_]){re.escape(variable)}"
        right_ok = "(?![A-Za-z0-9_])"
        if re.search(left_ok + right_ok, poly):
            found.append(variable)
    return found


def candidate_touches_unmeasured(case: dict, candidates: list[str]) -> bool:
    measured = set(case.get("measured_vars", []))
    for candidate in candidates:
        if set(vars_in_poly(candidate, case["variables"])) - measured:
            return True
    return False


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
    if not polynomials or not measured:
        return False, False
    gb = sp.groebner(polynomials, *order, order="lex")
    elim = [g.as_expr() for g in gb.polys if set(g.as_expr().free_symbols).issubset(set(measured))]
    if not elim:
        return False, False
    gb_elim = sp.groebner(elim, *measured, order="lex")
    weak = sp.expand(gb_elim.reduce(target_expr)[1]) == 0
    strong = any(poly_equal_up_to_scalar(g, target_expr, measured) for g in elim)
    return bool(weak), bool(strong)


def canonical_recovered(case: dict, candidates: list[str]) -> bool:
    variables = case["variables"]
    symbols = symbol_table(variables)
    order = [symbols[v] for v in variables]
    polynomials = [sympify_poly(p, symbols) for p in case["remaining_axioms"] + candidates]
    if not polynomials:
        return False
    gb = sp.groebner(polynomials, *order, order="lex")
    for missing_axiom in case["removed_axioms"]:
        missing = sympify_poly(missing_axiom, symbols)
        if sp.expand(gb.reduce(missing)[1]) != 0:
            return False
    return True


def score_case(case: dict) -> tuple[bool, bool]:
    """Return (has_derivable_candidate, canonical_success).

    New method outputs include enough symbolic data for the evaluator to
    recompute validity independently. Older outputs are accepted through a
    compatibility path so historical scores remain readable.
    """
    required = {"variables", "measured_vars", "targets", "remaining_axioms", "removed_axioms"}
    if not required.issubset(case):
        return bool(case.get("num_accepted", 0) > 0), bool(case.get("success"))
    if sp is None:
        if len(case.get("removed_indices", [])) > 1:
            return bool(case.get("num_accepted", 0) > 0), bool(case.get("coupled_success", case.get("success")))
        return bool(case.get("num_accepted", 0) > 0), bool(case.get("success"))
    if case.get("status") != "ok":
        return False, False
    has_derivable = False
    has_strong_derivable = False
    has_canonical = False
    has_coupled = False
    for item in case.get("accepted", []):
        candidates = item.get("candidates", [])
        derives_all = True
        strong_all = True
        for target in case["targets"]:
            target_vars = vars_in_poly(target, case["variables"])
            measured_subset = [v for v in case["measured_vars"] if v in target_vars]
            weak, strong = groebner_derives(
                case["variables"],
                measured_subset,
                case["remaining_axioms"],
                candidates,
                target,
            )
            if not weak:
                derives_all = False
                break
            strong_all = strong_all and strong
        if derives_all:
            has_derivable = True
            has_strong_derivable = has_strong_derivable or strong_all
            if candidate_touches_unmeasured(case, candidates):
                has_coupled = True
            if canonical_recovered(case, candidates):
                has_canonical = True
    if len(case.get("removed_indices", [])) > 1:
        return has_coupled, has_coupled
    return has_derivable, has_canonical


def summarize_cases(cases: list[dict], problem_filter: set[str] | None = None, size: int | None = None) -> dict:
    selected = []
    for case in cases:
        if problem_filter is not None and case["problem"] not in problem_filter:
            continue
        if size is not None and len(case["removed_indices"]) != size:
            continue
        selected.append(case)
    total = len(selected)
    completed = sum(1 for c in selected if c.get("status") == "ok")
    scored = [score_case(c) for c in selected]
    derivable = sum(1 for has_derivable, _ in scored if has_derivable)
    success = sum(1 for _, has_canonical in scored if has_canonical)
    return {
        "cases_total": total,
        "cases_completed": completed,
        "success_count": success,
        "success_rate": success / total if total else 0.0,
        "derivable_candidate_count": derivable,
        "derivable_candidate_rate": derivable / total if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", default=["scoring/ai_noether_exact_outputs.json"])
    parser.add_argument("--output", default="scoring/scores.json")
    parser.add_argument(
        "--include-multi",
        action="store_true",
        help="Include exploratory multi-axiom diagnostics in the score file.",
    )
    args = parser.parse_args()

    cases = []
    for input_path in args.input:
        payload = json.loads(Path(input_path).read_text())
        cases.extend(payload.get("cases", []))

    by_problem = defaultdict(list)
    for case in cases:
        by_problem[case["problem"]].append(case)

    scores = {
        "experiments": {
            "exact_single_axiom_core": {
                "results": {
                    "ai_noether_exact": summarize_cases(
                        cases, {"simple_harmonic_oscillator", "kepler"}, size=1
                    )
                }
            }
        }
    }
    all_single = summarize_cases(cases, size=1)
    if all_single["cases_total"] == 75:
        scores["experiments"]["exact_single_axiom_all_paper"] = {
            "results": {
                "ai_noether_exact": all_single
            }
        }
    if "simple_harmonic_oscillator" in by_problem:
        scores["experiments"]["simple_harmonic_single_axiom"] = {
            "results": {
                "ai_noether_exact": summarize_cases(cases, {"simple_harmonic_oscillator"}, size=1)
            }
        }
    if "kepler" in by_problem:
        scores["experiments"]["kepler_single_axiom"] = {
            "results": {
                "ai_noether_exact": summarize_cases(cases, {"kepler"}, size=1)
            }
        }
        if args.include_multi and any(c["problem"] == "kepler" and len(c["removed_indices"]) == 2 for c in cases):
            scores["experiments"]["kepler_pair_axiom"] = {
                "results": {
                    "ai_noether_exact": summarize_cases(cases, {"kepler"}, size=2)
                }
            }
        if args.include_multi and any(c["problem"] == "kepler" and len(c["removed_indices"]) == 3 for c in cases):
            scores["experiments"]["kepler_triple_axiom"] = {
                "results": {
                    "ai_noether_exact": summarize_cases(cases, {"kepler"}, size=3)
                }
            }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
