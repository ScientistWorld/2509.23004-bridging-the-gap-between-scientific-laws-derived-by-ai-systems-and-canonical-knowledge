#!/usr/bin/env python3
"""Run the actual implementation, optionally increasing its search budget.

No evaluator or saved answers are imported. Only the reference method and
packaged physical systems are used. The seed reaches Singular through its
documented --random command-line option.
"""
import argparse
import importlib.util
import itertools
import json
import os
from pathlib import Path
import random
import sys
import time
from types import SimpleNamespace

ROOT = Path('/home/user')


def load_method():
    spec = importlib.util.spec_from_file_location('audit_reference_method', ROOT / 'method/exact_abduction_runner.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=11)
    parser.add_argument('--stronger', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    module = load_method()
    os.environ['AUDIT_SINGULAR_SEED'] = str(args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(
        singular=str(ROOT / 'redteam/singular_seed.sh'),
        timeout_decomposition=300, timeout_case=600,
        max_candidate_size=1, filter_degenerate=False,
        saturate_nondegenerate=False,
    )
    payload = {'method': out.parent.name, 'seed': args.seed, 'complete': False,
               'algorithm': 'encode_primary_decompose_reason', 'cases': []}
    original_singular = module.run_singular
    search_order = None

    def ordered_singular(variables, *pos, **kwargs):
        order = variables if search_order is None else [variables[i] for i in search_order]
        return original_singular(order, *pos, **kwargs)

    module.run_singular = ordered_singular
    # Repeated ideal membership uses the same algebra, with cached bases.
    # This changes runtime, never the generated equations or acceptance test.
    if args.stronger:
        from functools import lru_cache
        @lru_cache(maxsize=2048)
        def basis(generators, variables):
            symbols = module.symbol_table(list(variables))
            gb = module.sp.groebner(
                [module.sympify_poly(p, symbols) for p in generators],
                *[symbols[v] for v in variables], order='lex', domain=module.sp.QQ)
            return gb, symbols
        def cached_implied(poly, generators, variables):
            if not generators:
                return False
            gb, symbols = basis(tuple(generators), tuple(variables))
            return module.sp.expand(gb.reduce(module.sympify_poly(poly, symbols))[1]) == 0
        module.implied_by_ideal = cached_implied
    for name in ['simple_harmonic_oscillator', 'kepler']:
        problem = module.read_problem(ROOT / 'data/systems_and_phenomena' / name / 'system.txt', name)
        sizes = [1] if name != 'kepler' else [1, 2, 3]
        orders = [None]
        if args.stronger:
            orders += [list(reversed(range(len(problem.variables))))]
            rng = random.Random(args.seed)
            for _ in range(2):
                order = list(range(len(problem.variables)))
                rng.shuffle(order)
                orders.append(order)
        for size in sizes:
            settings.max_candidate_size = (6 if size > 1 else 2) if args.stronger else (1 if size == 1 else -1)
            settings.filter_degenerate = size > 1
            settings.timeout_decomposition = 300 if size == 1 else 120
            settings.timeout_case = 600 if args.stronger or size == 1 else 120
            for combo in itertools.combinations(range(len(problem.equations)), size):
                start = time.monotonic()
                combined = None
                for order_id, order in enumerate(orders):
                    search_order = order
                    case = module.run_case(problem, combo, settings, out.parent / 'work' / f'order_{order_id}')
                    print(name, combo, 'order', order_id, case['status'], 'accepted', case['num_accepted'], flush=True)
                    if combined is None:
                        combined = case
                    elif case['status'] == 'ok':
                        if combined['status'] != 'ok':
                            combined = case
                        else:
                            known = {tuple(c['candidates']) for c in combined['accepted']}
                            combined['accepted'].extend(c for c in case['accepted'] if tuple(c['candidates']) not in known)
                combined['num_accepted'] = len(combined['accepted'])
                combined['runtime_seconds'] = time.monotonic() - start
                payload['cases'].append(combined)
                out.write_text(json.dumps(payload, indent=2))
    payload['complete'] = True
    out.write_text(json.dumps(payload, indent=2))
    print('Wrote', out, flush=True)


if __name__ == '__main__':
    main()
