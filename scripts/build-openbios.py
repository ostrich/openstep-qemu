#!/usr/bin/env python3
"""Build the pinned SPARC32 OpenBIOS patchset in a new output directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cross-prefix', required=True)
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'upstream.json').read_text())['projects']['openbios']
    for tool in ('gcc', 'ld', 'ar', 'as', 'strip', 'objcopy'):
        if not shutil.which(args.cross_prefix + tool):
            parser.error('Missing ELF cross tool: ' + args.cross_prefix + tool)
    for tool in ('make', 'cc', 'xsltproc', 'toke'):
        if not shutil.which(tool):
            parser.error('Missing host tool: ' + tool)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'source'
    build = output / 'build'
    subprocess.run(['git', 'clone', '--no-checkout',
                    str(args.source_checkout.resolve()), str(source)], check=True)
    subprocess.run(['git', 'checkout', '--detach', config['revision']],
                   cwd=source, check=True)
    patches = root / config['patches']
    hashes = {}
    for line in (patches / 'series').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        patch = patches / line
        hashes[line] = hashlib.sha256(patch.read_bytes()).hexdigest()
        subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
    subprocess.run(['python3', str(root / 'tests/risc/test-romvec-mmap.py'),
                    '--source', str(source)], check=True)
    build.mkdir()
    env = dict(os.environ, CROSS_COMPILE=args.cross_prefix)
    subprocess.run([str(source / 'config/scripts/switch-arch'), 'builtin-sparc32'],
                   cwd=build, env=env, check=True)
    with (output / 'build.log').open('wb') as log:
        subprocess.run(['make', '-j', str(args.jobs)], cwd=build, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    firmware = output / 'openbios-sparc32'
    shutil.copyfile(build / 'obj-sparc32/openbios-builtin.elf', firmware)
    tools = {}
    for name, command in [('cross_gcc', args.cross_prefix + 'gcc'),
                          ('host_cc', 'cc'), ('toke', 'toke')]:
        result = subprocess.run([command, '--version'], capture_output=True, text=True)
        tools[name] = (result.stdout + result.stderr).splitlines()[:3]
    (output / 'BUILD.json').write_text(json.dumps({
        'revision': config['revision'], 'patch_sha256': hashes, 'tools': tools,
        'firmware_sha256': hashlib.sha256(firmware.read_bytes()).hexdigest(),
        'configuration': 'builtin-sparc32',
    }, indent=2) + '\n')
    print(firmware)


if __name__ == '__main__':
    main()
