#!/usr/bin/env python3
"""Validate one complete four-host build, then publish its verified assets."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import quote
from sources import inputs
from version import current_version

HOSTS = ('linux-x86_64', 'macos-arm64', 'macos-x86_64', 'windows-x86_64')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bundle_manifest(path, root):
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate archive members')
            files = {name: archive.read(name) for name in names if not name.endswith('/')}
    else:
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            if len(members) != len({member.name for member in members}):
                raise ValueError('Duplicate archive members')
            if any(not (member.isdir() or member.isfile()) for member in members):
                raise ValueError('Unexpected bundle link/special file')
            files = {member.name: archive.extractfile(member).read() for member in members if member.isfile()}
    if any(not name.startswith(root + '/') or '..' in Path(name).parts for name in files):
        raise ValueError('Bundle contains an unexpected path')
    manifest = json.loads(files[root + '/BUILD.json'])
    hashes = json.loads(files[root + '/SHA256.json'])
    if set(hashes) != {name.removeprefix(root + '/') for name in files} - {'SHA256.json'}:
        raise ValueError('Bundle checksum manifest does not cover every payload file')
    for name, expected in hashes.items():
        if hashlib.sha256(files[root + '/' + name]).hexdigest() != expected:
            raise ValueError('Bundle payload checksum mismatch: ' + name)
    if any('qemu-system-x86_64' in Path(name).name for name in files):
        raise ValueError('Download unexpectedly contains the x86_64 emulator')
    executable = '.exe' if manifest['platform'] == 'windows' else ''
    for program in ('qemu-system-i386', 'qemu-img'):
        if root + '/bin/' + program + executable not in files:
            raise ValueError('Missing distributed executable: ' + program)
    for name in ('bios.bin', 'bios-256k.bin'):
        bios = files.get(root + '/share/qemu/' + name)
        if bios is None or hashlib.sha256(bios).hexdigest() != manifest['firmware']['bios_sha256']:
            raise ValueError('Bundle BIOS does not match its firmware manifest')
    return manifest

def prepare(directory, output, version, commit):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Invalid release commit')
    if output.exists() or output.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Use a new candidate directory outside the downloaded artifacts')
    expected = {}
    common_firmware = None
    sources = {project: inputs(project) for project in ('qemu', 'seabios')}
    for host in HOSTS:
        base = 'openstep-qemu-' + version + '-' + host
        expected[base + ('.zip' if host.startswith('windows-') else '.tar.gz')] = (base, host, False)
        expected[base + '-source.tar.gz'] = (base, host, True)
    found = {}
    for path in directory.rglob('*'):
        if path.is_file() and path.name in expected:
            if path.is_symlink() or path.name in found:
                raise ValueError('Duplicate/symlink release asset: ' + path.name)
            found[path.name] = path
    if set(found) != set(expected):
        raise ValueError('Missing host archives: ' + ', '.join(sorted(set(expected) - set(found))))
    for name, path in found.items():
        fields = path.with_name(name + '.sha256').read_text().split()
        if fields != [sha(path), name]:
            raise ValueError('Invalid checksum sidecar: ' + name)
        root, host, is_source = expected[name]
        if is_source:
            with tarfile.open(path) as archive:
                identity = json.loads(archive.extractfile('source/SOURCE-BUILD.json').read())
                for project, entry in sources.items():
                    for patch in entry['patch_sha256']:
                        content = archive.extractfile('recipes/' + entry['patches'] + '/' + patch['file']).read()
                        if hashlib.sha256(content).hexdigest() != patch['sha256']:
                            raise ValueError('Source archive patch drift: ' + name)
        else:
            identity = bundle_manifest(path, root)
            platform, architecture = host.rsplit('-', 1)
            if identity['platform'] != platform or identity['architecture'] != architecture:
                raise ValueError('Wrong host in bundle: ' + name)
            if not identity['qtests'] or any(result['exit_code'] or result['passed'] <= result.get('skipped', 0)
                                              for result in identity['qtests'].values()):
                raise ValueError('Bundle lacks passing regression results: ' + name)
            firmware = identity['firmware']
            if (firmware['source'] != sources['seabios']
                    or firmware['config_sha256'] != sha(Path(__file__).resolve().parents[1] / 'configs/seabios.config')
                    or firmware['extra_version'] != '-openstep-' + version):
                raise ValueError('Unexpected firmware inputs: ' + name)
            if common_firmware is None:
                common_firmware = firmware
            elif firmware != common_firmware:
                raise ValueError('Host bundles do not share the same verified firmware')
        if (identity['distribution_version'] != version or identity['repository_commit'] != commit
                or identity['sources'] != sources):
            raise ValueError('Mixed version/commit/source inputs: ' + name)
    output.mkdir(parents=True)
    # Keep source and sidecars in CI artifacts for validation. Public downloads
    # consist of exactly one binary archive per host.
    for name, path in sorted(found.items()):
        if not expected[name][2]:
            shutil.copy2(path, output / name)
    assets = [{'name': path.name, 'sha256': sha(path), 'bytes': path.stat().st_size}
              for path in sorted(output.iterdir())]
    manifest = {'schema': 1, 'version': version, 'commit': commit, 'hosts': list(HOSTS), 'assets': assets}
    (output / ('openstep-qemu-' + version + '-release.json')).write_text(json.dumps(manifest, indent=2) + '\n')
    print('Verified all four hosts, matching source, firmware and checksums')
    return manifest

class GitHub:
    def __init__(self, repo):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise ValueError('Invalid repository')
        self.repo = repo
    def api(self, method, path, payload=None, missing=False):
        command = ['gh', 'api', '--method', method, 'repos/' + self.repo + '/' + path]
        if payload is not None:
            command += ['--input', '-']
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True)
        if result.returncode:
            if missing and 'HTTP 404' in result.stderr:
                return None
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else None
    def upload(self, tag, path):
        subprocess.run(['gh', 'release', 'upload', tag, str(path), '--repo', self.repo], check=True)
    def asset_matches(self, asset, path):
        if asset.get('digest'):
            return asset['digest'] == 'sha256:' + sha(path)
        content = subprocess.check_output(['gh', 'api', 'repos/' + self.repo + '/releases/assets/' + str(asset['id']),
                                           '-H', 'Accept: application/octet-stream'])
        return hashlib.sha256(content).hexdigest() == sha(path)

def publish(directory, version, commit, tag, github):
    manifest_path = directory / ('openstep-qemu-' + version + '-release.json')
    manifest = json.loads(manifest_path.read_text())
    if manifest['commit'] != commit or manifest['version'] != version or manifest['hosts'] != list(HOSTS):
        raise ValueError('Release candidate identity mismatch')
    required_names = {'openstep-qemu-' + version + '-' + host +
                      ('.zip' if host.startswith('windows-') else '.tar.gz')
                      for host in HOSTS}
    if (len(manifest['assets']) != 4 or
            {asset['name'] for asset in manifest['assets']} != required_names):
        raise ValueError('Release must contain exactly four host binary archives')
    paths = []
    for asset in manifest['assets']:
        if Path(asset['name']).name != asset['name']:
            raise ValueError('Invalid candidate asset path')
        path = directory / asset['name']
        if path.is_symlink() or path.stat().st_size != asset['bytes'] or sha(path) != asset['sha256']:
            raise ValueError('Release candidate changed: ' + asset['name'])
        paths.append(path)
    rolling = tag == 'master-build'
    if not rolling and tag != 'v' + version:
        raise ValueError('Version tag does not match candidate')
    def current_master():
        return github.api('GET', 'git/ref/heads/master')['object']['sha'] == commit
    if rolling and not current_master():
        print('Superseded master commit; publication skipped')
        return
    if not rolling:
        ref = github.api('GET', 'git/ref/tags/' + quote(tag, safe=''))['object']
        while ref['type'] == 'tag':
            ref = github.api('GET', 'git/tags/' + ref['sha'])['object']
        if ref['type'] != 'commit' or ref['sha'] != commit:
            raise ValueError('Version tag no longer identifies this build commit')
    release = github.api('GET', 'releases/tags/' + quote(tag, safe=''), missing=True)
    existing = list(release['assets']) if release else []
    by_name = {asset['name']: asset for asset in existing}
    if release and not rolling and not release['draft']:
        if set(by_name) == {path.name for path in paths} and all(github.asset_matches(by_name[path.name], path) for path in paths):
            print('Identical versioned release already published')
            return
        raise ValueError('Refusing to replace an already-published versioned release')
    if release is None:
        release = github.api('POST', 'releases', {'tag_name': tag, 'target_commitish': commit,
                                                 'name': tag, 'draft': True, 'prerelease': rolling})
    for path in paths:
        if path.name in by_name:
            if not github.asset_matches(by_name[path.name], path):
                raise ValueError('Existing release asset differs: ' + path.name)
        else:
            github.upload(tag, path)
    # Existing successful assets remain until the entire new upload completes.
    if rolling:
        if not current_master():
            print('Master advanced during upload; prior release retained')
            return
        if github.api('GET', 'git/ref/tags/master-build', missing=True) is None:
            github.api('POST', 'git/refs', {'ref': 'refs/tags/master-build', 'sha': commit})
        else:
            github.api('PATCH', 'git/refs/tags/master-build', {'sha': commit, 'force': True})
    prerelease = rolling or '-' in version
    body = ('Build commit: `' + commit + '`.\n\n'
            'Linux x86-64, Windows x86-64, macOS arm64 and macOS x86-64 bundles, '
            'from one successful workflow run.\n\n'
            'Downloads contain qemu-system-i386 and qemu-img. See the bundled README '
            'and repository release notes for current guest-support limits.\n')
    github.api('PATCH', 'releases/' + str(release['id']),
               {'name': 'Latest master build' if rolling else 'OPENSTEP QEMU ' + tag,
                'body': body, 'draft': False, 'prerelease': prerelease,
                'make_latest': 'false' if prerelease else 'true'})
    if rolling:
        names = {path.name for path in paths}
        for asset in existing:
            if asset['name'].startswith('openstep-qemu-') and asset['name'] not in names:
                github.api('DELETE', 'releases/assets/' + str(asset['id']))
    print('Published ' + tag)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare', 'publish'))
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--commit', required=True)
    p.add_argument('--tag')
    p.add_argument('--repo')
    args = p.parse_args()
    version = current_version()
    if args.command == 'prepare':
        if args.output is None:
            p.error('prepare requires --output')
        prepare(args.directory, args.output, version, args.commit)
    else:
        if not args.repo or not args.tag:
            p.error('publish requires --repo and --tag')
        publish(args.directory, version, args.commit, args.tag, GitHub(args.repo))

if __name__ == '__main__':
    main()
