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
    return {'source': inputs('seabios'), 'config_sha256': digest(ROOT / 'configs/seabios.config'),
            'extra_version': '-openstep-' + version}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('record', 'verify'))
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    actual = {**expected(), 'bios_sha256': digest(args.directory / 'bios.bin')}
    manifest = args.directory / 'BUILD.json'
    if args.command == 'record':
        manifest.write_text(json.dumps(actual, indent=2) + '\n')
    elif json.loads(manifest.read_text()) != actual:
        raise SystemExit('Firmware source/config/hash does not match this checkout')
    print('Firmware ' + args.command + ' passed')

if __name__ == '__main__':
    main()
