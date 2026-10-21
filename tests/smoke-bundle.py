#!/usr/bin/env python3
"""Check packaged binaries/firmware through their shipped entry points using TCG."""
import argparse
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path

def smoke(bundle, arch, machine, firmware):
    extension = '.exe' if os.name == 'nt' else ''
    emulator = bundle / 'bin' / ('qemu-system-' + arch + extension)
    subprocess.run([str(emulator), '--version'], check=True)
    subprocess.run([str(bundle / 'bin' / ('qemu-img' + extension)), '--version'], check=True)
    # Hold the listening port until QEMU connects, avoiding port-allocation races.
    with socket.socket() as listener, tempfile.TemporaryFile() as diagnostics:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(30)
        port = listener.getsockname()[1]
        command = [str(emulator), '-L', str(bundle / 'share/qemu'),
                   '-bios', str(bundle / 'share/qemu' / firmware),
                   '-machine', machine, '-accel', 'tcg', '-m', '64', '-display', 'none', '-nic', 'none',
                   '-monitor', 'none', '-serial', 'none',
                   '-qmp', f'tcp:127.0.0.1:{port},server=off']
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=diagnostics, stderr=diagnostics)
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(30)
                with connection.makefile('rb') as stream:
                    greeting = json.loads(stream.readline())
                    assert 'QMP' in greeting, greeting
                    for operation in ('qmp_capabilities', 'query-status', 'quit'):
                        request = {'execute': operation, 'id': operation}
                        connection.sendall((json.dumps(request) + '\n').encode())
                        if operation == 'quit':
                            # QEMU can close TCP before its final reply is flushed.
                            # A clean process exit is the shutdown acknowledgement.
                            break
                        while True:
                            line = stream.readline()
                            assert line, f'QMP disconnected during {operation}'
                            response = json.loads(line)
                            if response.get('id') == operation:
                                break
                        assert 'return' in response, response
                        if operation == 'query-status':
                            assert response['return']['status'] == 'running', response
            assert process.wait(timeout=30) == 0, 'QEMU exited unsuccessfully'
        except Exception as error:
            diagnostics.seek(0)
            detail = diagnostics.read().decode(errors='replace')
            raise RuntimeError(f'Bundle QMP smoke test failed: {error}\n{detail}') from error
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    print(arch + ': bundled entry point and disk-free TCG firmware startup passed')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    args = p.parse_args()
    bundle = args.bundle.resolve()
    # OpenBIOS can silently fall back to serial when the TCX FCode is absent.
    # A QMP-only startup check would otherwise accept a broken desktop bundle.
    if not (bundle / 'share/qemu/QEMU,tcx.bin').is_file():
        raise RuntimeError('Bundle is missing SPARC TCX framebuffer firmware')
    for case in [('i386', 'pc,acpi=off,hpet=off,usb=off', 'bios-256k.bin'),
                 ('sparc', 'SS-5', 'openbios-sparc32'),
                 ('hppa', '715', 'hppa-firmware.img')]:
        smoke(bundle, *case)

if __name__ == '__main__':
    main()
