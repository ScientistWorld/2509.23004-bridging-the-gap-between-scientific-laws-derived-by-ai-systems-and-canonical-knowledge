#!/usr/bin/env python3
"""Install one attempt; train-evaluate, then hidden-test with NO arguments.

Only scoring output artifacts and visible train score shape are changed. The
gym's evaluator files, process and Python environment are never modified.
Every call restores the non-audit workspace on completion, including failures.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/home/user')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()
    name = args.name
    folder = ROOT / 'redteam' / name
    folder.mkdir(parents=True, exist_ok=True)
    scoring = ROOT / 'scoring'
    affected = list(scoring.glob('*_outputs.json')) + [scoring/'scores_train.json', scoring/'scores_test.json']
    previous = {p: p.read_bytes() for p in affected if p.exists()}
    started = time.monotonic()
    status = {'name': name, 'train_exit': None, 'test_exit': None,
              'test_command': 'bash scripts/evaluate_test.sh',
              'test_has_arguments': False}
    try:
        for p in affected:
            p.unlink(missing_ok=True)
        with (folder/'generation.log').open('w') as log:
            if name.startswith('reference_seed_') or name == 'honest_stronger':
                seed = int(name.rsplit('_', 1)[1]) if name.startswith('reference_seed_') else 11
                artifact = folder/'candidates.json'
                if not artifact.exists() or not json.loads(artifact.read_text()).get('complete'):
                    cmd = ['python', 'redteam/generate_reference.py', '--seed', str(seed), '--output', str(artifact)]
                    if name == 'honest_stronger':
                        cmd += ['--stronger']
                    subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                shutil.copyfile(artifact, scoring/'audit_outputs.json')
            else:
                subprocess.run(['python', 'redteam/prepare_shortcut.py', name], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
        shutil.copyfile(scoring/'audit_outputs.json', folder/'candidates.json')
        with (folder/'evaluation.log').open('w') as log:
            train = subprocess.run(['bash', 'scripts/evaluate_train.sh'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            status['train_exit'] = train.returncode
            if (scoring/'scores_train.json').exists():
                shutil.copyfile(scoring/'scores_train.json', folder/'scores_train.json')
            if name == 'shortcut_empty_shape':
                (scoring/'scores_train.json').write_text('{"experiments": {}}\n')
            if name == 'shortcut_unlisted_method':
                # A new failed method is present on disk after the final train
                # evaluation; train score alignment silently drops its row.
                late = json.loads((scoring/'audit_outputs.json').read_text())
                late['method'] = 'shortcut_late_failed_method'
                for case in late['cases']:
                    case['status'] = 'error'
                    case['accepted'] = []
                (scoring/'late_outputs.json').write_text(json.dumps(late))
                shutil.copyfile(scoring/'late_outputs.json', folder/'late_candidates.json')
            if name == 'shortcut_move_baseline':
                # No rank metric actually compares to the baseline. Confirm it
                # cannot provide a genuine gain by moving that comparison.
                baseline = json.loads((scoring/'audit_outputs.json').read_text())
                baseline['method'] = 'no_abduction_baseline'
                for case in baseline['cases']:
                    case['accepted'] = []
                    case['status'] = 'error'
                (scoring/'baseline_outputs.json').write_text(json.dumps(baseline))
            # The forged-score test intentionally leaves its prewritten file.
            # All other tests start with no score, detecting non-writing failures.
            if name != 'shortcut_forged_flags':
                (scoring/'scores_test.json').unlink(missing_ok=True)
            test = subprocess.run(['bash', 'scripts/evaluate_test.sh'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            status['test_exit'] = test.returncode
            if (scoring/'scores_test.json').exists():
                shutil.copyfile(scoring/'scores_test.json', folder/'scores_test.json')
            else:
                (folder/'scores_test.json').unlink(missing_ok=True)
            if (scoring/'scores_train.json').exists():
                shutil.copyfile(scoring/'scores_train.json', folder/'scores_train_submitted.json')
    except Exception as exc:
        status['exception'] = repr(exc)
        raise
    finally:
        status['elapsed_seconds'] = time.monotonic() - started
        (folder/'status.json').write_text(json.dumps(status, indent=2))
        for p in list(scoring.glob('*_outputs.json')) + [scoring/'scores_train.json', scoring/'scores_test.json']:
            p.unlink(missing_ok=True)
        for p, content in previous.items():
            p.write_bytes(content)
    print(name, status, flush=True)


if __name__ == '__main__':
    main()
