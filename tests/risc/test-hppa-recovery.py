#!/usr/bin/env python3
"""Diskless PA-RISC recovery-counter checks using QEMU's CPU debug interface."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import traceback
from risc_control import Guest


class Remote:
    def __init__(self, directory):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(4)
        self.reg_bytes = 4
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            self.sock.connect('/proc/self/fd/%d/debug.sock' % fd)
        finally:
            os.close(fd)

    def packet(self, command):
        data = command.encode()
        self.sock.sendall(b'$' + data + b'#%02x' % (sum(data) & 255))
        while True:
            ch = self.sock.recv(1)
            if not ch:
                raise RuntimeError('Debug connection closed')
            if ch == b'-':
                raise RuntimeError('Debug packet rejected')
            if ch == b'$':
                break
        data = bytearray()
        while True:
            ch = self.sock.recv(1)
            if ch == b'#':
                break
            if not ch:
                raise RuntimeError('Truncated debug packet')
            data += ch
        checksum = self.sock.recv(2)
        if int(checksum, 16) != sum(data) & 255:
            raise RuntimeError('Debug checksum mismatch')
        self.sock.sendall(b'+')
        return data.decode()

    def put(self, reg, value):
        assert self.packet('P%x=%s' % (reg, value.to_bytes(self.reg_bytes, 'big').hex())) == 'OK'

    def get(self, reg):
        return int(self.packet('p%x' % reg), 16)

    def memory(self, address, data):
        assert self.packet('M%x,%x:%s' % (address, len(data), data.hex())) == 'OK'

    def step(self):
        reply = self.packet('s')
        assert reply.startswith(('T05', 'S05')), reply


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['qemu', 'bios', 'data', 'output']:
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument("--expect-original", action="store_true",
                   help="Require the original model to fail counting, trap and branch cases")
    p.add_argument("--machine", default="715")
    p.add_argument("--cpu", default="pa-7300lc")
    p.add_argument("--case", action="append", dest="selected_cases")
    p.add_argument("--skip-migration", action="store_true",
                   help="CPU-only qualification when board migration is unsupported")
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cases = ['disabled', 'count', 'nullified', 'negative-before-fetch',
             'break-rollback', 'load-fault-rollback', 'branch-delay-nullify']
    if not a.expect_original and not a.skip_migration:
        cases.append('migration')
    if a.selected_cases:
        if not set(a.selected_cases).issubset(cases):
            p.error('Unknown case')
        cases = [case for case in cases if case in a.selected_cases]
    results = {}
    for case in cases:
        d = out / case
        d.mkdir()
        command = [str(a.qemu.resolve()), '-machine', a.machine, '-cpu', a.cpu, '-m', '64',
                   '-bios', str(a.bios.resolve()), '-L', str(a.data.resolve()),
                   '-S', '-display', 'none', '-nic', 'none', '-serial', 'none',
                   '-monitor', 'none', '-gdb', 'unix:debug.sock,server=on,wait=off',
                   '-qmp', 'unix:qmp.sock,server=on,wait=off']
        (d / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        remote = None
        with (d / 'qemu.log').open('wb') as log:
            proc = subprocess.Popen(command, cwd=d, stdout=log, stderr=log,
                                    start_new_session=True)
            try:
                end = time.monotonic() + 4
                while not (d / 'debug.sock').exists():
                    if proc.poll() is not None or time.monotonic() > end:
                        raise RuntimeError('QEMU readiness failed')
                    time.sleep(.02)
                r = remote = Remote(d)
                r.packet('qSupported')
                r.reg_bytes = len(r.packet('p0')) // 2
                assert r.reg_bytes in [4, 8]
                r.packet('?')
                r.put(0, 0)
                r.put(33, 0x10000)
                r.put(35, 0x10004)
                r.put(34, 0)
                r.put(36, 0)
                r.memory(0x10000, bytes.fromhex('08000240' * 4))
                r.put(51, 2)
                if case == 'disabled':
                    r.step(); r.step()
                    assert r.get(51) == 2
                elif case == 'count':
                    r.put(0, 0x10)
                    for value in [1, 0, 0xffffffff]:
                        r.step()
                        assert r.get(51) == value, (r.get(51), value)
                    assert r.packet('Z0,60,4') == 'OK'
                    assert r.packet('c').startswith(('T05', 'S05'))
                    assert r.get(33) == 0x60
                    assert r.get(41) & 0x10
                elif case == 'migration':
                    # Migrate a prepared recovery-enabled CPU. QEMU cannot
                    # restore its unrelated GDB 'debug' global runstate.
                    r.put(0, 0x10)
                    r.put(51, 1)
                    r.put(33, 0x10004)
                    r.put(35, 0x10008)
                    image = d / 'migration.bin'
                    guest = Guest(d)
                    guest.qmp('stop')
                    guest.qmp('migrate', {'uri': 'file:' + str(image)})
                    end = time.monotonic() + 8
                    while True:
                        status = guest.qmp('query-migrate')['status']
                        if status == 'completed':
                            break
                        if status in ['failed', 'cancelled'] or time.monotonic() > end:
                            raise RuntimeError('Migration failed: ' + status)
                        time.sleep(.02)
                    guest.qmp('quit')
                    proc.wait(timeout=4)
                    r.sock.close()
                    remote = None
                    proc = subprocess.Popen(command + ['-incoming', 'file:' + str(image)],
                                            cwd=d, stdout=log, stderr=log,
                                            start_new_session=True)
                    end = time.monotonic() + 4
                    while True:
                        try:
                            state = Guest(d).qmp('query-migrate').get('status')
                            if state != 'completed':
                                if time.monotonic() > end:
                                    raise RuntimeError('Incoming migration not ready')
                                time.sleep(.02)
                                continue
                            r = remote = Remote(d)
                            break
                        except OSError:
                            if proc.poll() is not None or time.monotonic() > end:
                                raise RuntimeError('Migration destination failed')
                            time.sleep(.02)
                    r.packet('qSupported')
                    r.reg_bytes = len(r.packet('p0')) // 2
                    assert r.get(51) == 1 and r.get(33) == 0x10004
                    assert r.get(0) & 0x10
                    r.step()
                    assert r.get(51) == 0 and r.get(33) == 0x10008
                    image.unlink()
                elif case == 'nullified':
                    r.put(0, 0x200010)
                    r.step()
                    assert r.get(51) == 2 and r.get(33) == 0x10004
                    assert not r.get(0) & 0x200000
                elif case == 'branch-delay-nullify':
                    r.memory(0x10000, bytes.fromhex('e8000002ffffffff08000240'))
                    r.put(0, 0x10)
                    r.step()
                    assert r.get(51) == 1 and r.get(33) == 0x10004
                    assert r.get(0) & 0x200000
                    r.step()
                    assert r.get(51) == 1 and r.get(33) == 0x10008
                else:
                    vector = {'negative-before-fetch': 0x60,
                              'break-rollback': 0x120,
                              'load-fault-rollback': 0x1e0}[case]
                    if case == 'negative-before-fetch':
                        r.put(51, 0xffffffff)
                        r.put(33, 0x40000000)
                        r.put(35, 0x40000004)
                    else:
                        r.put(51, 0)
                        r.memory(0x10000, bytes.fromhex('00010004' if case == 'break-rollback' else '48220000'))
                        r.put(1, 0x40000000)
                    r.put(0, 0x12 if case == 'load-fault-rollback' else 0x10)
                    assert r.packet('Z0,%x,4' % vector) == 'OK'
                    assert r.packet('c').startswith(('T05', 'S05'))
                    assert r.get(33) == vector, hex(r.get(33))
                    assert r.get(51) == (0xffffffff if case == 'negative-before-fetch' else 0)
                results[case] = {'passed': True, 'pc': r.get(33), 'counter': r.get(51)}
            except Exception as error:
                results[case] = {'passed': False, 'error': repr(error), 'traceback': traceback.format_exc()}
            finally:
                if remote:
                    remote.sock.close()
                try:
                    Guest(d).qmp('quit')
                except (OSError, RuntimeError):
                    pass
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=4)
        (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(case, results[case], flush=True)
    expected_failures = {'count', 'negative-before-fetch', 'branch-delay-nullify'} if a.expect_original else set()
    matched = all(row['passed'] == (case not in expected_failures)
                  for case, row in results.items())
    (out / 'qualification.json').write_text(json.dumps({
        'expected_original': a.expect_original, 'matched_expectations': matched,
        'expected_failures': sorted(expected_failures)}, indent=2) + '\n')
    raise SystemExit(0 if matched else 1)


if __name__ == '__main__':
    main()
