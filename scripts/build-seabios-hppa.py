#!/usr/bin/env python3
"""Build the pinned 32-bit SeaBIOS-HPPA firmware in a new output directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-checkout', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cross-prefix', required=True)
    p.add_argument('--jobs', type=int, default=8)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'upstream.json').read_text())['projects']['seabios-hppa']
    for tool in ('gcc', 'ld', 'as', 'objcopy', 'objdump', 'strip'):
        if not shutil.which(a.cross_prefix + tool):
            p.error('Missing ELF cross tool: ' + a.cross_prefix + tool)
    for tool in ('make', 'cc', 'python'):
        if not shutil.which(tool):
            p.error('Missing host tool: ' + tool)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    subprocess.run(['git', 'clone', '--no-checkout', str(a.source_checkout.resolve()),
                    str(source)], check=True)
    subprocess.run(['git', 'checkout', '--detach', config['revision']], cwd=source, check=True)
    base = root / config['patches']
    hashes = {}
    for name in (base / 'series').read_text().splitlines():
        patch = base / name
        hashes[name] = hashlib.sha256(patch.read_bytes()).hexdigest()
        subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
    subprocess.run(['python3', str(root / 'tests/risc/test-boot-alignment.py'),
                    '--source', str(source)], check=True)
    build = out / 'build'
    env = dict(os.environ)
    with (out / 'build.log').open('wb') as log:
        subprocess.run(['make', '-f', 'Makefile.parisc', '-j', str(a.jobs),
                        'OUT=' + str(build) + '/', 'BITS=32', 'BIT_SUFFIX=',
                        'CROSS_PREFIX=' + a.cross_prefix], cwd=source, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    firmware = out / 'hppa-firmware.img'
    shutil.copyfile(build / 'hppa-firmware.img', firmware)
    subprocess.run([a.cross_prefix + 'strip', '--strip-debug', str(firmware)], check=True)
    version = subprocess.check_output([a.cross_prefix + 'gcc', '--version'], text=True)
    (out / 'BUILD.json').write_text(json.dumps({
        'revision': config['revision'], 'patch_sha256': hashes,
        'cross_gcc': version.splitlines()[0], 'bits': 32,
        'firmware_sha256': hashlib.sha256(firmware.read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    print(firmware)


if __name__ == '__main__':
    main()
