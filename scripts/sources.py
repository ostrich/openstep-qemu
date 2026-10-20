#!/usr/bin/env python3
"""Fetch exact upstream commits and apply the complete checked patch sets."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(*args, cwd=None, capture=False):
    return subprocess.check_output(args, cwd=cwd, text=True) if capture else subprocess.run(args, cwd=cwd, check=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inputs(project):
    pins = json.loads((ROOT / 'upstream.json').read_text())
    entry = pins['projects'][project]
    base = ROOT / entry['patches']
    names = (base / 'series').read_text().splitlines()
    if not names or len(names) != len(set(names)) or set(names) != {p.name for p in base.glob('*.patch')}:
        raise ValueError(project + ': series must cover every patch exactly once')
    patches = []
    for number, name in enumerate(names, 1):
        if not re.fullmatch(r'[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.patch', name) or not name.startswith(f'{number:04d}-'):
            raise ValueError('Invalid patch name/order: ' + name)
        path = base / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Invalid patch file: ' + name)
        if not path.read_text().startswith(f'Subject: [PATCH {number}/{len(names)}] '):
            raise ValueError('Subject numbering mismatch: ' + name)
        patches.append({'file': name, 'sha256': digest(path)})
    topic_names = []
    for topic in entry['topics']:
        topic_names.extend((base / 'topics' / (topic + '.series')).read_text().splitlines())
    if len(topic_names) != len(names) or set(topic_names) != set(names):
        raise ValueError(project + ': topics must partition the complete ordered series')
    positions = {name: index for index, name in enumerate(names)}
    for topic in entry['topics']:
        selected = (base / 'topics' / (topic + '.series')).read_text().splitlines()
        if selected != sorted(selected, key=positions.__getitem__):
            raise ValueError(project + ': topic order must follow the complete series')
    if not re.fullmatch('[0-9a-f]{40}', entry['revision']):
        raise ValueError('Upstream must be pinned to a full Git commit')
    return {**entry, 'patch_sha256': patches}

def index_digest(source):
    return hashlib.sha256(subprocess.check_output(['git', 'diff', '--cached', '--binary', 'HEAD'], cwd=source)).hexdigest()

def verify(source, expected, state):
    if state['inputs'] != expected:
        raise ValueError('Pins or patches changed; preserve this checkout and use a new source directory')
    if run('git', 'rev-parse', 'HEAD', cwd=source, capture=True).strip() != expected['revision']:
        raise ValueError('Checkout revision changed')
    run('git', 'diff', '--quiet', cwd=source)
    if run('git', 'ls-files', '--others', '--exclude-standard', cwd=source, capture=True).strip():
        raise ValueError('Unexpected untracked source files; refusing to overwrite them')
    if index_digest(source) != state['index_sha256']:
        raise ValueError('Applied source differs from the recorded patch set')

def prepare(project):
    expected = inputs(project)
    source = ROOT / '.sources' / project
    state_path = ROOT / 'work' / ('source-' + project + '.json')
    if state_path.exists():
        verify(source, expected, json.loads(state_path.read_text()))
        print(project + ': exact pinned/patched source already prepared', flush=True)
        return
    if source.exists():
        raise ValueError('Unrecorded source directory exists: ' + str(source) + '; preserve it and investigate')
    source.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    print('Fetching ' + project + ' ' + expected['revision'], flush=True)
    run('git', 'init', '-q', str(source))
    run('git', 'config', 'core.autocrlf', 'false', cwd=source)
    run('git', 'remote', 'add', 'origin', expected['url'], cwd=source)
    run('git', 'fetch', '--depth=1', 'origin', expected['revision'], cwd=source)
    run('git', 'checkout', '--detach', 'FETCH_HEAD', cwd=source)
    for patch in expected['patch_sha256']:
        print('Applying ' + patch['file'], flush=True)
        run('git', 'apply', '--index', str(ROOT / expected['patches'] / patch['file']), cwd=source)
    state = {'inputs': expected, 'index_sha256': index_digest(source)}
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    verify(source, expected, state)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'prepare', 'verify'))
    parser.add_argument('--project', choices=('qemu', 'seabios', 'openbios', 'seabios-hppa', 'all'), default='all')
    args = parser.parse_args()
    projects = tuple(json.loads((ROOT / 'upstream.json').read_text())['projects']) if args.project == 'all' else (args.project,)
    for project in projects:
        expected = inputs(project)
        if args.command == 'prepare':
            prepare(project)
        elif args.command == 'verify':
            verify(ROOT / '.sources' / project, expected,
                   json.loads((ROOT / 'work' / ('source-' + project + '.json')).read_text()))
        else:
            print(project + ': patch names, subjects, topics and pin passed')

if __name__ == '__main__':
    main()
