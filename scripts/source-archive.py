#!/usr/bin/env python3
"""Capture patched source, fetched subprojects and this repository's build recipes."""
import argparse
import gzip
import io
import json
import platform
import os
import subprocess
import tarfile
from pathlib import Path
from sources import ROOT, inputs, digest, verify
from version import current_version

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    host = {'Darwin': 'macos', 'Windows': 'windows', 'Linux': 'linux'}[platform.system()]
    arch = platform.machine().lower().replace('aarch64', 'arm64').replace('amd64', 'x86_64')
    version = current_version()
    destination = (args.output or ROOT / 'dist' / ('openstep-qemu-' + version + '-' + host + '-' + arch + '-source.tar.gz')).resolve()
    destination.relative_to(ROOT / 'dist')
    if destination.exists():
        raise FileExistsError('Preserve existing source archive')
    for project in ('qemu', 'seabios'):
        verify(ROOT / '.sources' / project, inputs(project),
               json.loads((ROOT / 'work' / ('source-' + project + '.json')).read_text()))
    destination.parent.mkdir(exist_ok=True)
    def clean(member):
        if any(part in ('.git', '__pycache__') for part in Path(member.name).parts):
            return None
        member.uid = member.gid = 0
        member.uname = member.gname = 'root'
        member.mtime = 0
        return member
    with destination.open('xb') as output, gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for project in ('qemu', 'seabios'):
                tar.add(ROOT / '.sources' / project, arcname='source/' + project, filter=clean)
                if project == 'seabios':
                    content = (inputs(project)['version'] + '\n').encode()
                    member = tarfile.TarInfo('source/seabios/.version')
                    member.size = len(content); member.mode = 0o644
                    tar.addfile(member, io.BytesIO(content))
            identity = {'schema': 1, 'distribution_version': version,
                        'repository_commit': os.environ.get('GITHUB_SHA'),
                        'sources': {project: inputs(project) for project in ('qemu', 'seabios')}}
            content = (json.dumps(identity, indent=2) + '\n').encode()
            member = tarfile.TarInfo('source/SOURCE-BUILD.json')
            member.size = len(content); member.mode = 0o644
            tar.addfile(member, io.BytesIO(content))
            for name in ('upstream.json', 'COPYING', 'README.md', 'build', 'scripts', 'configs', 'patches', 'tests', 'docs', 'launch'):
                tar.add(ROOT / name, arcname='recipes/' + name, filter=clean)
    destination.with_name(destination.name + '.sha256').write_text(digest(destination) + '  ' + destination.name + '\n')
    print(destination)

if __name__ == '__main__':
    main()
