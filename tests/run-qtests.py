#!/usr/bin/env python3
"""Run device/SCSI regressions on i386, with optional extended x86_64 coverage, retaining TAP logs."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--extended', action='store_true', help='Also run AMD DMA tests on a built x86_64 emulator')
    args = p.parse_args()
    build, output = args.build.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['TMPDIR'] = str(output)
    extension = '.exe' if os.name == 'nt' else ''
    env['QTEST_QEMU_IMG'] = str(build / ('qemu-img' + extension))
    results = {}
    def run(label, command, minimum):
        r = subprocess.run(command, cwd=build, env=env, capture_output=True, text=True, timeout=600)
        log = r.stdout + r.stderr
        (output / (label + '.log')).write_text(log)
        passed = len(re.findall(r'^ok \d+(?: |$)', log, re.M))
        if r.returncode or passed < minimum:
            raise RuntimeError(f'{label}: exit={r.returncode}, passed={passed}; inspect {output / (label + ".log")}')
        results[label] = {'passed': passed, 'skipped': len(re.findall(r'^ok \d+.*# SKIP', log, re.M)), 'exit_code': r.returncode}
        print(f'{label}: {passed} passed', flush=True)
    suites = [('i8259-test', 5), ('sb16-test', 1), ('ide-test', 1),
              ('display-vga-test', 1), ('am53c974-test', 11),
              ('am53c974-dma-test', 47), ('fuzz-virtio-scsi-test', 1)]
    for arch in (('i386', 'x86_64') if args.extended else ('i386',)):
        env['QTEST_QEMU_BINARY'] = str(build / ('qemu-system-' + arch + extension))
        for suite, minimum in suites:
            if arch == 'x86_64' and suite != 'am53c974-dma-test':
                continue
            run(arch + '-' + suite, [str(build / 'tests/qtest' / (suite + extension))], minimum)
    env['QTEST_QEMU_BINARY'] = str(build / ('qemu-system-i386' + extension))
    qos = str(build / 'tests/qtest' / ('qos-test' + extension))
    run('pcnet', [qos, '-p', '/i386/pc/i440FX-pcihost/pci-bus-pc/pci-bus/pcnet/pcnet-tests'], 7)
    listing = subprocess.check_output([qos, '-l'], cwd=build, env=env, text=True)
    paths = [line[2:].strip() for line in listing.splitlines()
             if line.startswith('# /') and '/virtio-scsi-pci/' in line]
    if len(paths) < 7:
        raise RuntimeError('Virtio-SCSI cases missing from QoS enumeration')
    for index, path in enumerate(paths):
        run('virtio-scsi-' + str(index), [qos, '-p', path], 1)
    (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')

if __name__ == '__main__':
    main()
