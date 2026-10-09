#!/usr/bin/env python3
"""Check packaged binaries/firmware through their shipped entry points using TCG."""
import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    args = p.parse_args()
    bundle = args.bundle.resolve()
    extension = '.exe' if os.name == 'nt' else ''
    emulator = bundle / 'bin' / ('qemu-system-i386' + extension)
    subprocess.run([str(emulator), '--version'], check=True)
    subprocess.run([str(bundle / 'bin' / ('qemu-img' + extension)), '--version'], check=True)
    command = [str(emulator), '-L', str(bundle / 'share/qemu'),
               '-bios', str(bundle / 'share/qemu/bios-256k.bin'),
               '-machine', 'pc,acpi=off,hpet=off,usb=off', '-accel', 'tcg',
               '-cpu', 'pentium', '-m', '32', '-display', 'none', '-nic', 'none',
               '-monitor', 'none', '-serial', 'none', '-qmp', 'stdio']
    # Send the complete bounded QMP exchange through stdio on every host.
    requests = ''.join(json.dumps({'execute': command}) + '\n'
                       for command in ('qmp_capabilities', 'query-status', 'quit'))
    result = subprocess.run(command, input=requests, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    messages = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert any('QMP' in message for message in messages), 'No QMP greeting'
    assert any(message.get('return', {}).get('status') == 'running' for message in messages), messages
    print('Bundle entry points and disk-free TCG firmware startup passed')

if __name__ == '__main__':
    main()
