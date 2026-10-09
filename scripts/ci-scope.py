#!/usr/bin/env python3
"""Select PR hosts; releases and manual builds always cover every host."""
import os
import subprocess
from pathlib import Path


def hosts(paths):
    selected = set()
    for path in paths:
        if path != 'docs/bundle.md' and (path.startswith('docs/') or path.endswith('.md')):
            continue
        if path in ('build/linux.sh', 'build/windows.sh', 'build/macos.sh'):
            selected.add(Path(path).stem)
        elif path == 'launch/openstep.ps1':
            selected.add('windows')
        elif path == 'launch/openstep.sh':
            selected.update(('linux', 'macos'))
        else:
            selected.update(('linux', 'macos', 'windows'))
    return selected


if __name__ == '__main__':
    selected = {'linux', 'macos', 'windows'}
    if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request':
        paths = subprocess.check_output(
            ['git', 'diff', '--name-only', '-z', os.environ['BASE'] + '...HEAD'],
            text=True).split('\0')
        selected = hosts(filter(None, paths))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for host in ('macos', 'windows'):
            output.write(f'{host}={str(host in selected).lower()}\n')
