#!/usr/bin/env python3
"""One validated build identity for firmware, bundles and source archives."""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def current_version(env=None):
    env = os.environ if env is None else env
    explicit = env.get('OPENSTEP_VERSION')
    ref = env.get('GITHUB_REF', '')
    if explicit:
        value = explicit
    elif ref.startswith('refs/tags/v'):
        value = ref.removeprefix('refs/tags/v')
    elif env.get('GITHUB_SHA'):
        sha = env['GITHUB_SHA']
        if not re.fullmatch('[0-9a-f]{40}', sha):
            raise ValueError('Invalid build commit')
        prefix = 'master' if ref == 'refs/heads/master' else 'dev'
        run = env.get('GITHUB_RUN_ID', 'local')
        attempt = env.get('GITHUB_RUN_ATTEMPT', '1')
        if not re.fullmatch(r'(?:[0-9]+|local)', run) or not attempt.isdigit():
            raise ValueError('Invalid workflow run identity')
        value = f'{prefix}-{sha[:12]}-{run}-{attempt}'
    else:
        value = json.loads((ROOT / 'upstream.json').read_text())['distribution_version']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,95}', value):
        raise ValueError('Invalid distribution version')
    return value

def archive_stem(host, commit=None):
    """Readable download identity; full build/run identity stays in manifests."""
    commit = os.environ.get('GITHUB_SHA') if commit is None else commit
    if commit is not None and not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Invalid archive commit')
    qemu = json.loads((ROOT / 'upstream.json').read_text())['projects']['qemu']['version']
    suffix = commit[:7] if commit else 'local'
    return f'openstep-qemu-{qemu}-{suffix}-{host}'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--github-env', action='store_true')
    args = parser.parse_args()
    version = current_version()
    if args.github_env:
        with Path(os.environ['GITHUB_ENV']).open('a') as file:
            file.write('OPENSTEP_VERSION=' + version + '\n')
    print(version)

if __name__ == '__main__':
    main()
