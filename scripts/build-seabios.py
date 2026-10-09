#!/usr/bin/env python3
"""Build from an exported patched tree to avoid dirty-build host/date strings."""
import argparse
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from sources import ROOT, inputs, verify
from version import current_version

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--jobs', default='4')
    args = p.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'out')
    entry = inputs('seabios')
    source = ROOT / '.sources/seabios'
    verify(source, entry, json.loads((ROOT / 'work/source-seabios.json').read_text()))
    tree = subprocess.check_output(['git', 'write-tree'], cwd=source, text=True).strip()
    blob = subprocess.check_output(['git', 'archive', tree], cwd=source)
    output.mkdir(parents=True, exist_ok=True)
    version = current_version()
    # Disposable input snapshot is local to this build; source checkouts remain intact.
    with tempfile.TemporaryDirectory(prefix='seabios-input-', dir=output.parent) as directory:
        snapshot = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
            tar.extractall(snapshot, filter='data')
        (snapshot / '.version').write_text(entry['version'] + '\n')
        shutil.copy2(ROOT / 'configs/seabios.config', snapshot / '.config')
        options = ['OUT=' + str(output) + '/', 'EXTRAVERSION=-openstep-' + version]
        subprocess.run(['make', '-C', str(snapshot), *options, 'olddefconfig'], check=True)
        # Force regeneration of version/link inputs when reusing the output directory.
        subprocess.run(['make', '-B', '-C', str(snapshot), *options, '-j', args.jobs], check=True)
    header = (output / 'autoversion.h').read_text()
    expected = '#define BUILD_VERSION "' + entry['version'] + '-openstep-' + version + '"'
    if expected not in header:
        raise RuntimeError('SeaBIOS version contains unexpected host/date/dirty metadata')

if __name__ == '__main__':
    main()
