#!/usr/bin/env python3
"""Run a diskless SPARC ROM matrix for microSPARC-II reserved PTE bits."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

from risc_control import Guest

CPUS = ('Fujitsu-MB86904', 'TI-MicroSparc-II', 'TI-SuperSparc-40')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True,
                        help='QEMU pc-bios directory')
    parser.add_argument('--cross-prefix', required=True,
                        help='ELF cross tools, e.g. /path/bin/sparc-linux-')
    parser.add_argument('--output', type=Path, required=True,
                        help='New evidence directory')
    parser.add_argument('--expect-original', action='store_true',
                        help='Verify the original model fails reserved-bit cases')
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.qemu = args.qemu.resolve()
    args.data = args.data.resolve()
    for tool in ('gcc', 'ld'):
        if not shutil.which(args.cross_prefix + tool):
            parser.error('Missing cross tool: ' + args.cross_prefix + tool)
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name('microsparc-pte.S')
    for level in (1, 2, 3):
        for bits in (0, 0xf8000000):
            obj = args.output / f'pte-{level}-{bits:x}.o'
            subprocess.run([args.cross_prefix + 'gcc', '-c', '-m32', '-mcpu=v8',
                            f'-DLEAF_LEVEL={level}', f'-DRESERVED=0x{bits:x}',
                            str(source), '-o', str(obj)], check=True)
            subprocess.run([args.cross_prefix + 'ld', '-m', 'elf32_sparc',
                            '-Ttext', '0xffd00000', '-e', '_start', '-o',
                            str(obj.with_suffix('.elf')), str(obj)], check=True)

    def run(case):
        cpu, level, bits = case
        directory = args.output / f'{cpu}-{level}-{bits:x}'
        directory.mkdir()
        rom = args.output / f'pte-{level}-{bits:x}.elf'
        command = [str(args.qemu), '-machine', 'SS-5', '-cpu', cpu, '-m', '64',
                   '-bios', str(rom), '-display', 'none', '-nic', 'none',
                   '-serial', 'none', '-monitor', 'none', '-qmp',
                   'unix:qmp.sock,server=on,wait=off', '-L', str(args.data)]
        (directory / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        values = []
        with (directory / 'qemu.log').open('wb') as log:
            process = subprocess.Popen(
                command, cwd=directory, stdout=log, stderr=subprocess.STDOUT,
                preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            guest = Guest(directory)
            try:
                deadline = time.monotonic() + 4
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        text = guest.qmp('human-monitor-command',
                                         {'command-line': 'xp /3wx 0x1003000'},
                                         timeout=.5)
                        values = [int(v, 16) for v in
                                  re.findall(r'0x([0-9a-fA-F]{8})', text)]
                        if len(values) == 3 and values[2] == 0x50415353:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(.03)
            finally:
                if process.poll() is None:
                    guest.qmp('quit')
                process.wait(timeout=3)
        executed = len(values) == 3 and values[2] == 0x50415353
        expected = not bits or (not args.expect_original and
                                cpu != 'TI-SuperSparc-40')
        passed = executed == expected
        if executed:
            ppn = 0x100000 | (0x200 if level == 3 else 0)
            passed &= values[0] == 0x13579bdf and values[1] & 0xffffff00 == ppn
        else:
            passed &= 'Trap 0x21' in (directory / 'qemu.log').read_text()
        result = {'cpu': cpu, 'leaf_level': level, 'reserved': hex(bits),
                  'executed': executed, 'expected_execution': expected,
                  'report': [hex(v) for v in values], 'passed': bool(passed)}
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

    cases = [(cpu, level, bits) for cpu in CPUS for level in (1, 2, 3)
             for bits in (0, 0xf8000000)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, cases))
    (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    failures = [r for r in results if not r['passed']]
    print(f'{len(results) - len(failures)}/{len(results)} expected outcomes passed')
    if failures:
        raise SystemExit(json.dumps(failures, indent=2))


if __name__ == '__main__':
    main()
