#!/usr/bin/env python3
"""Held-out test-slice evaluator for exact symbolic abduction artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    import sympy as sp
except ModuleNotFoundError:  # pragma: no cover - login-node compatibility path
    sp = None


SLICE_NAME = "test"
SPLIT_NAME = "grouped_alternating_v3_primary_metric_calibrated"
EXPECTED_TOTALS_BY_SLICE = {
    "train": {
        "exact_single_axiom_all_paper": 36,
        "exact_single_axiom_core": 5,
        "simple_harmonic_single_axiom": 2,
        "kepler_single_axiom": 3,
        "kepler_pair_axiom": 5,
        "kepler_triple_axiom": 5,
    },
    "test": {
        "exact_single_axiom_all_paper": 39,
        "exact_single_axiom_core": 6,
        "simple_harmonic_single_axiom": 4,
        "kepler_single_axiom": 2,
        "kepler_pair_axiom": 5,
        "kepler_triple_axiom": 5,
    },
}
FULL_TOTALS_BY_EXPERIMENT = {
    "exact_single_axiom_all_paper": 75,
    "exact_single_axiom_core": 11,
    "simple_harmonic_single_axiom": 6,
    "kepler_single_axiom": 5,
    "kepler_pair_axiom": 10,
    "kepler_triple_axiom": 10,
}
FIXED_SPLITS = {
    ("simple_harmonic_oscillator", 1): {
        "train": {(1,), (3,)},
        "test": {(2,), (4,), (5,), (6,)},
    },
    ("kepler", 2): {
        "train": {(1, 2), (1, 5), (2, 3), (2, 4), (3, 5)},
        "test": {(1, 3), (1, 4), (2, 5), (3, 4), (4, 5)},
    },
    ("kepler", 3): {
        "train": {(1, 2, 3), (1, 2, 5), (1, 3, 5), (1, 4, 5), (2, 3, 4)},
        "test": {(1, 2, 4), (1, 3, 4), (2, 3, 5), (2, 4, 5), (3, 4, 5)},
    }
}


def symbol_table(variables: list[str]) -> dict[str, sp.Symbol]:
    if sp is None:
        raise RuntimeError("SymPy is required to recompute symbolic evaluation metrics.")
    return {name: sp.Symbol(name) for name in variables}


def sympify_poly(poly: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    return sp.sympify(poly.replace("^", "**"), locals=symbols)


def poly_equal_up_to_scalar(a: sp.Expr, b: sp.Expr, variables: list[sp.Symbol]) -> bool:
    pa = sp.Poly(sp.expand(a), *variables, domain=sp.QQ)
    pb = sp.Poly(sp.expand(b), *variables, domain=sp.QQ)
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
    gb = sp.groebner(polynomials, *order, order="lex", domain=sp.QQ)
    elim = [g.as_expr() for g in gb.polys if set(g.as_expr().free_symbols).issubset(set(measured))]
    if not elim:
        return False, False
    gb_elim = sp.groebner(elim, *measured, order="lex", domain=sp.QQ)
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
    gb = sp.groebner(polynomials, *order, order="lex", domain=sp.QQ)
    for missing_axiom in case["removed_axioms"]:
        missing = sympify_poly(missing_axiom, symbols)
        if sp.expand(gb.reduce(missing)[1]) != 0:
            return False
    return True


def implied_by_ideal(poly: str, generators: list[str], variables: list[str]) -> bool:
    if not generators:
        return False
    symbols = symbol_table(variables)
    order = [symbols[v] for v in variables]
    gb = sp.groebner([sympify_poly(p, symbols) for p in generators], *order, order="lex", domain=sp.QQ)
    return sp.expand(gb.reduce(sympify_poly(poly, symbols))[1]) == 0


def candidate_is_degenerate(case: dict, candidates: list[str]) -> bool:
    return any(
        implied_by_ideal(factor, case["remaining_axioms"] + candidates, case["variables"])
        for factor in case.get("nonzero_factors", [])
    )


def score_case(case: dict) -> tuple[bool, bool, bool]:
    required = {"variables", "measured_vars", "targets", "remaining_axioms", "removed_axioms"}
    if not required.issubset(case):
        if case.get("num_accepted", 0) or case.get("success") or case.get("accepted"):
            raise ValueError(
                f"Case {case.get('problem')} {case.get('removed_indices')} reports candidates "
                "or success without symbolic fields required for independent evaluation."
            )
        return False, False, False
    if sp is None:
        if case.get("accepted") or case.get("num_accepted", 0) or case.get("success"):
            raise RuntimeError("SymPy is required to evaluate non-empty symbolic method outputs.")
        return False, False, False
    if case.get("status") != "ok":
        return False, False, False
    has_derivable = False
    has_strong_derivable = False
    has_canonical = False
    has_coupled = False
    has_degenerate = False
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
            if candidate_is_degenerate(case, candidates):
                has_degenerate = True
                continue
            has_derivable = True
            has_strong_derivable = has_strong_derivable or strong_all
            if candidate_touches_unmeasured(case, candidates):
                has_coupled = True
            if canonical_recovered(case, candidates):
                has_canonical = True
    if len(case.get("removed_indices", [])) > 1:
        return has_derivable, has_coupled, has_degenerate
    return has_derivable, has_canonical, has_degenerate


def case_identity(case: dict) -> str:
    stable = {
        "problem": case.get("problem"),
        "removed_indices": case.get("removed_indices", []),
        "targets": case.get("targets", []),
        "measured_vars": case.get("measured_vars", []),
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def case_sort_key(case: dict) -> tuple:
    return (
        str(case.get("problem", "")),
        len(case.get("removed_indices", [])),
        tuple(case.get("removed_indices", [])),
        json.dumps(case.get("targets", []), sort_keys=True),
    )


def selected_for_slice(case: dict, ordinal: int) -> str:
    fixed_split = FIXED_SPLITS.get((case.get("problem"), len(case.get("removed_indices", []))))
    if fixed_split is not None:
        removed = tuple(case.get("removed_indices", []))
        if removed in fixed_split["train"]:
            return "train"
        if removed in fixed_split["test"]:
            return "test"
        raise ValueError(f"Case {case.get('problem')} {removed} is missing from fixed split.")
    group_key = f"{case.get('problem')}|{len(case.get('removed_indices', []))}"
    offset = int(hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % 2
    return "train" if (ordinal + offset) % 2 == 0 else "test"


def slice_cases(cases: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for case in cases:
        grouped[(case.get("problem", ""), len(case.get("removed_indices", [])))].append(case)
    selected = []
    for group_cases in grouped.values():
        for ordinal, case in enumerate(sorted(group_cases, key=case_sort_key)):
            if selected_for_slice(case, ordinal) == SLICE_NAME:
                selected.append(case)
    return sorted(selected, key=case_sort_key)


def summarize_cases(
    cases: list[dict],
    problem_filter: set[str] | None = None,
    size: int | None = None,
    expected_total: int | None = None,
    full_total: int | None = None,
) -> dict:
    selected = []
    for case in cases:
        if problem_filter is not None and case["problem"] not in problem_filter:
            continue
        if size is not None and len(case["removed_indices"]) != size:
            continue
        selected.append(case)
    total = max(len(selected), expected_total or 0)
    completed = sum(1 for c in selected if c.get("status") == "ok")
    scored = [score_case(c) for c in selected]
    derivable = sum(1 for has_derivable, _, _ in scored if has_derivable)
    success = sum(1 for _, has_success, _ in scored if has_success)
    degenerate = sum(1 for _, _, has_degenerate in scored if has_degenerate)
    success_rate = success / total if total else 0.0
    success_signal = success_rate + 0.001 * (success / full_total if full_total else 0.0)
    derivable_candidate_rate = derivable / total if total else 0.0
    return {
        "cases_total": total,
        "cases_completed": completed,
        "success_count": success,
        "success_rate": success_rate,
        "success_signal": success_signal,
        "derivable_candidate_count": derivable,
        "derivable_candidate_rate": derivable_candidate_rate,
        "degenerate_candidate_count": degenerate,
        "nondegenerate_candidate_rate": 1.0 - (degenerate / total) if total else 0.0,
    }


def add_summary(
    scores: dict,
    experiment: str,
    method_name: str,
    cases: list[dict],
    problem_filter: set[str] | None = None,
    size: int | None = None,
) -> None:
    scores["experiments"].setdefault(experiment, {"results": {}})
    expected_total = EXPECTED_TOTALS_BY_SLICE[SLICE_NAME].get(experiment)
    full_total = FULL_TOTALS_BY_EXPERIMENT.get(experiment)
    summary = summarize_cases(
        cases, problem_filter, size, expected_total, full_total
    )
    if experiment == "kepler_triple_axiom":
        summary["derivable_success_signal"] = summary["derivable_candidate_rate"] + 0.001 * (
            summary["success_count"] / full_total if full_total else 0.0
        )
    scores["experiments"][experiment]["results"][method_name] = summary


def method_name_for_payload(payload: dict, input_path: Path) -> str:
    return payload.get("method") or input_path.stem.removesuffix("_outputs")


def load_cases_by_method(input_paths: list[str]) -> dict[str, list[dict]]:
    cases_by_method: dict[str, dict[str, dict]] = defaultdict(dict)
    for raw_path in input_paths:
        input_path = Path(raw_path)
        payload = json.loads(input_path.read_text())
        method_name = method_name_for_payload(payload, input_path)
        for case in payload.get("cases", []):
            cases_by_method[method_name][case_identity(case)] = case
    return {
        method_name: list(cases_by_identity.values())
        for method_name, cases_by_identity in cases_by_method.items()
    }


def build_scores(
    cases_by_method: dict[str, list[dict]],
    include_multi: bool,
    include_triples: bool,
) -> dict:
    scores = {"slice": SLICE_NAME, "split": SPLIT_NAME, "experiments": {}}
    for method_name, method_cases in sorted(cases_by_method.items()):
        slice_method_cases = slice_cases(method_cases)
        add_summary(
            scores,
            "exact_single_axiom_core",
            method_name,
            slice_method_cases,
            {"simple_harmonic_oscillator", "kepler"},
            size=1,
        )
        add_summary(scores, "exact_single_axiom_all_paper", method_name, slice_method_cases, size=1)
        add_summary(
            scores,
            "simple_harmonic_single_axiom",
            method_name,
            slice_method_cases,
            {"simple_harmonic_oscillator"},
            size=1,
        )
        add_summary(
            scores,
            "kepler_single_axiom",
            method_name,
            slice_method_cases,
            {"kepler"},
            size=1,
        )
        if include_multi:
            add_summary(
                scores,
                "kepler_pair_axiom",
                method_name,
                slice_method_cases,
                {"kepler"},
                size=2,
            )
        if include_triples:
            add_summary(
                scores,
                "kepler_triple_axiom",
                method_name,
                slice_method_cases,
                {"kepler"},
                size=3,
            )
    return scores


def train_score_shape(path: Path) -> tuple[dict[str, list[str]], set[str]]:
    payload = json.loads(path.read_text())
    shape = {}
    methods = set()
    for experiment, experiment_payload in payload.get("experiments", {}).items():
        experiment_methods = sorted(experiment_payload.get("results", {}).keys())
        shape[experiment] = experiment_methods
        methods.update(experiment_methods)
    return shape, methods


def align_to_train_scores(scores: dict, train_scores_path: Path, available_methods: set[str]) -> dict:
    shape, required_methods = train_score_shape(train_scores_path)
    missing_methods = sorted(required_methods - available_methods)
    if missing_methods:
        raise ValueError(
            "Test inputs are missing method artifacts already present in train scores: "
            + ", ".join(missing_methods)
        )
    aligned = {"slice": SLICE_NAME, "split": SPLIT_NAME, "experiments": {}}
    empty_summary = summarize_cases([])
    for experiment, methods in shape.items():
        aligned["experiments"][experiment] = {"results": {}}
        current_results = scores.get("experiments", {}).get(experiment, {}).get("results", {})
        for method_name in methods:
            aligned["experiments"][experiment]["results"][method_name] = current_results.get(
                method_name,
                empty_summary,
            )
    return aligned


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--include-multi", action="store_true")
    parser.add_argument("--include-triples", action="store_true")
    parser.add_argument(
        "--required-methods-from",
        help="Optional train scores file whose experiment/method shape must be mirrored.",
    )
    args = parser.parse_args()

    cases_by_method = load_cases_by_method(args.input)
    scores = build_scores(cases_by_method, args.include_multi, args.include_triples)
    if args.required_methods_from:
        scores = align_to_train_scores(scores, Path(args.required_methods_from), set(cases_by_method))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
