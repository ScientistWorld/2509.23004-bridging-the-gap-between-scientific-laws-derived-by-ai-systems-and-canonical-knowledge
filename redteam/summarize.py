#!/usr/bin/env python3
"""Report raw score deltas and the specified scale-normalized audit ranking.

The real attempt population is unknowable at audit time. Report our population
explicitly; componentwise ties/dominance are independent of that population.
"""
import json
from pathlib import Path
import statistics

ROOT = Path('/home/user/redteam')
configuration = json.loads((ROOT/'reference_checked_in/reference.json').read_text())['experiments']
reference = json.loads((ROOT/'reference_checked_in/scores_test.json').read_text())['experiments']
attempts = {}
for p in sorted(ROOT.glob('*/status.json')):
    status = json.loads(p.read_text())
    score_path = p.parent/'scores_test.json'
    attempts[p.parent.name] = {'status': status, 'scores': json.loads(score_path.read_text()) if score_path.exists() else None}

def values(scores, method):
    return {(e, m): r[method][m]
            for e, v in scores.get('experiments', {}).items()
            for r in [v.get('results', {})] if method in r and e in configuration
            for m, config in configuration[e]['metrics'].items()
            if abs(config['coefficient']) > 0 and m in r[method] and isinstance(r[method][m], (int,float))}

base = values({'experiments': reference}, 'ai_noether_exact')
fresh = values(attempts['reference_seed_11']['scores'], 'reference_seed_11')
rows = {'checked_in_reference': base}
for name, attempt in attempts.items():
    if attempt['scores'] is not None:
        rows[name] = values(attempt['scores'], name)

scales = {}
for key in base:
    observations = [v[key] for v in rows.values() if key in v]
    scales[key] = statistics.pstdev(observations) if len(observations)>1 else 0

def weight(key):
    e,m=key
    metric=configuration[e]['metrics'][m]
    return configuration[e]['weight'] * abs(metric['coefficient']) * (1 if metric['higher_is_better'] else -1)

summary = {'normalization': 'population std across checked-in reference and completed attempts listed below; missing values skipped; zero-spread metrics contribute 0',
           'reference': {'/'.join(k):v for k,v in base.items()},
           'fresh_reference': {'/'.join(k):v for k,v in fresh.items()},
           'metric_scales': {'/'.join(k):v for k,v in scales.items()}, 'attempts': {}}

def delta(row, anchor, normalized=False):
    return sum(weight(k)*(value-anchor[k])/(scales[k] if normalized else 1)
               for k,value in row.items() if k in anchor
               and (not normalized or scales[k]>0))

for name, attempt in attempts.items():
    row = rows.get(name, {})
    rankable = attempt['status']['test_exit'] == 0 and attempt['scores'] is not None
    summary['attempts'][name] = {
        'test_exit': attempt['status']['test_exit'],
        'elapsed_seconds': attempt['status']['elapsed_seconds'],
        'method_present': bool(row),
        'scored_metric_count': len(row),
        'rankable_completed_test': rankable,
        'weighted_raw_delta': delta(row, base) if rankable else None,
        'normalized_rank_delta': delta(row, base, True) if rankable else None,
        'weighted_raw_delta_vs_fresh': delta(row, fresh) if rankable else None,
        'normalized_rank_delta_vs_fresh': delta(row, fresh, True) if rankable else None,
        'metrics': {'/'.join(k):v for k,v in row.items()},
        'experiments': {e:v.get('results',{}).get(name) for e,v in (attempt['scores'] or {}).get('experiments',{}).items()},
    }
    if name == 'shortcut_unlisted_method':
        late = values(attempt['scores'], 'shortcut_late_failed_method')
        summary['attempts'][name]['late_method_present'] = bool(late)
        summary['attempts'][name]['late_method_rank_delta_if_missing_skipped'] = delta(late, base)
    print(name, json.dumps({k:v for k,v in summary['attempts'][name].items() if k not in ['metrics','experiments']}))

seed_rows = [rows[f'reference_seed_{seed}'] for seed in (11,23,47)]
summary['seed_spread'] = {
    'seeds': [11,23,47],
    'metric_max_minus_min': {'/'.join(k):max(row[k] for row in seed_rows)-min(row[k] for row in seed_rows) for k in base},
    'weighted_raw_rank_max_minus_min': max(delta(row,base) for row in seed_rows)-min(delta(row,base) for row in seed_rows),
    'normalized_rank_max_minus_min': max(delta(row,base,True) for row in seed_rows)-min(delta(row,base,True) for row in seed_rows),
}
(ROOT/'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True))
