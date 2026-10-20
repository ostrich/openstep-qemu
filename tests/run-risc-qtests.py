#!/usr/bin/env python3
"""Run bounded SPARC/HPPA regressions, optionally including shared x86 ESP tests."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--include-x86', action='store_true')
    p.add_argument('--skip-file-migration', action='store_true',
                   help='Exercise Windows file-migration exclusions on another host')
    a = p.parse_args()
    skip_file_migration = os.name == 'nt' or a.skip_file_migration
    build, out = a.build.resolve(), a.output.resolve()
    cases = [('sparc', 'esp-timing-test', 13), ('sparc', 'tcx-test', 4),
             ('hppa', 'ncr53c710-test', 19), ('hppa', 'lasi-test', 1),
             ('hppa', 'artist-test', 14)]
    if a.include_x86:
        cases += [('i386', 'am53c974-test', 11), ('i386', 'am53c974-dma-test', 47)]
    extension = '.exe' if os.name == 'nt' else ''
    for arch, name, _ in cases:
        for path in (build / ('qemu-system-' + arch + extension), build / 'tests/qtest' / (name + extension)):
            if not path.is_file():
                p.error('Build this target first: ' + str(path))
    out.mkdir(parents=True, exist_ok=False)

    def run(case):
        arch, name, minimum = case
        env = dict(os.environ, QTEST_QEMU_BINARY=str(build / ('qemu-system-' + arch)))
        command = [str(build / 'tests/qtest' / (name + extension))]
        expected_skips = 0
        if skip_file_migration:
            # QEMU's file migration channel cannot make Windows file handles
            # nonblocking. Keep these explicit TAP skips, as in the x86 runner.
            if name == 'esp-timing-test':
                command += ['-x', '/sparc/esp/migration']
                expected_skips = 5
            elif name == 'am53c974-dma-test':
                command += ['-x', '/i386/am53c974/migration']
                expected_skips = 9
            elif name == 'artist-test':
                command += ['-x', '/hppa/artist/recovery-migration']
                expected_skips = 1
        r = subprocess.run(command, env=env,
                           capture_output=True, text=True, timeout=180)
        log = r.stdout + r.stderr
        label = arch + '-' + name
        (out / (label + '.log')).write_text(log)
        passed = len(re.findall(r'^ok \d+(?: |$)(?![^\n]*# SKIP)', log, re.M))
        skipped = len(re.findall(r'^ok \d+[^\n]*# SKIP', log, re.M))
        if r.returncode or passed < minimum - expected_skips or skipped != expected_skips:
            raise RuntimeError(label + ': failed; inspect ' + str(out / (label + '.log')))
        return label, {'passed': passed, 'skipped': skipped, 'exit_code': r.returncode}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, cases))
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(sum(v['passed'] for v in results.values()), 'device tests passed')


if __name__ == '__main__':
    main()
