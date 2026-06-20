#!/usr/bin/env python3
"""Merge saved abduction output files by benchmark case key.

This is intentionally evaluator-side plumbing: it reads method-produced JSON
artifacts and combines partial reruns without importing or rerunning method
code. Later inputs replace earlier ones for the same method/problem/removal
case, which lets a targeted rerun repair stale cases while preserving the rest
of a broader sweep.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def case_key(case: dict) -> tuple[str, tuple[int, ...]]:
    return case["problem"], tuple(case.get("removed_indices", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    merged: dict[tuple[str, tuple[int, ...]], dict] = {}
    method = None
    algorithm = None
    problems: list[str] = []
    sizes: set[int] = set()
    axiom_limits: dict[str, int] = {}

    for input_path in args.input:
        payload = json.loads(Path(input_path).read_text())
        method = payload.get("method", method)
        algorithm = payload.get("algorithm", algorithm)
        for problem in payload.get("problems", []):
            if problem not in problems:
                problems.append(problem)
        sizes.update(int(size) for size in payload.get("sizes", []))
        axiom_limits.update(payload.get("axiom_limits", {}))
        for case in payload.get("cases", []):
            merged[case_key(case)] = case

    ordered_cases = [
        merged[key]
        for key in sorted(merged, key=lambda item: (item[0], len(item[1]), item[1]))
    ]
    output_payload = {
        "method": method or "ai_noether_exact",
        "algorithm": algorithm or "encode_primary_decompose_reason",
        "problems": problems,
        "sizes": sorted(sizes),
        "axiom_limits": axiom_limits,
        "cases": ordered_cases,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_payload, indent=2, sort_keys=True))
    print(f"Wrote {output_path} with {len(ordered_cases)} merged cases")


if __name__ == "__main__":
    main()
