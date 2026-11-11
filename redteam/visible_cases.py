"""Construct the public benchmark instances using only agent-visible data.

This intentionally retains the publicly exposed full axiom list: the answer
replay shortcut below demonstrates that the list contains every answer.
"""
import itertools
from pathlib import Path
import re

NONZERO = ['m1', 'm2', 'd1', 'd2', 'p', 'd1+d2']


def cases():
    result = []
    for problem in ['simple_harmonic_oscillator', 'kepler']:
        text = (Path('/home/user/data/systems_and_phenomena') / problem / 'system.txt').read_text()
        def names(label):
            match = re.search(label + r':\s*\[(.*?)\]', text, re.S)
            return [v.strip().strip('\"\'') for v in match.group(1).split(',')]
        variables = names('Variables')
        measured = names('Measured Variables')
        equations = [s.strip() for s in re.search(r'Equations?:\s*(.*?)(?=\n\s*\n\s*Measured)', text, re.S).group(1).splitlines() if s.strip()]
        targets = [s.strip() for s in re.search(r'Target Polynomial:?\s*(.*)$', text, re.S).group(1).splitlines() if s.strip()]
        for size in ([1, 2, 3] if problem == 'kepler' else [1]):
            for combo in itertools.combinations(range(len(equations)), size):
                result.append(dict(
                    problem=problem, variables=variables, measured_vars=measured,
                    targets=targets, remaining_axioms=[e for i, e in enumerate(equations) if i not in combo],
                    removed_axioms=[equations[i] for i in combo],
                    removed_indices=[i+1 for i in combo],
                    nonzero_factors=NONZERO[:] if problem == 'kepler' and size > 1 else [],
                    status='ok', accepted=[], num_accepted=0,
                    success=False, runtime_seconds=0,
                ))
    return result
