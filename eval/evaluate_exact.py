#!/usr/bin/env python3
"""Evaluate AI-Noether exact abduction outputs without importing method code."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def summarize_cases(cases: list[dict], problem_filter: set[str] | None = None, size: int | None = None) -> dict:
    selected = []
    for case in cases:
        if problem_filter is not None and case["problem"] not in problem_filter:
            continue
        if size is not None and len(case["removed_indices"]) != size:
            continue
        selected.append(case)
    total = len(selected)
    success = sum(1 for c in selected if c.get("success"))
    completed = sum(1 for c in selected if c.get("status") == "ok")
    derivable = sum(1 for c in selected if c.get("num_accepted", 0) > 0)
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
    parser.add_argument("--input", default="scoring/ai_noether_exact_outputs.json")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    cases = payload.get("cases", [])

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
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(scores, indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
