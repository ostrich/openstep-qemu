#!/usr/bin/env python3
"""Record/verify the shared patched ROM against exact source and config inputs."""
import argparse
import hashlib
import json
from pathlib import Path
from sources import ROOT, inputs, digest
from version import current_version

def expected():
    version = current_version()
    return {'sources': {p: inputs(p) for p in ('seabios', 'openbios', 'seabios-hppa')},
            'risc_configurations': {'openbios': 'builtin-sparc32', 'seabios-hppa': 'BITS=32'},
            'config_sha256': digest(ROOT / 'configs/seabios.config'),
            'extra_version': '-openstep-' + version}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('record', 'verify'))
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    actual = {**expected(), 'rom_sha256': {name: digest(args.directory / name)
              for name in ('bios.bin', 'openbios-sparc32', 'hppa-firmware.img')}}
    manifest = args.directory / 'BUILD.json'
    if args.command == 'record':
        manifest.write_text(json.dumps(actual, indent=2) + '\n')
    else:
        recorded = json.loads(manifest.read_text())
        if recorded != actual:
            differences = [key for key in sorted(recorded.keys() | actual.keys())
                           if recorded.get(key) != actual.get(key)]
            raise SystemExit('Firmware does not match this checkout: ' + ', '.join(differences))
    print('Firmware ' + args.command + ' passed')

if __name__ == '__main__':
    main()
