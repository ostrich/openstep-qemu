#!/usr/bin/env python3
"""Exercise release identity, candidate rejection and publication ordering offline."""
import hashlib
import importlib.util
import io
import json
import os
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import release
import version

COMMIT = 'a' * 40
VERSION = 'master-aaaaaaaaaaaa-123-1'

def digest(data):
    return hashlib.sha256(data).hexdigest()

class FakeGitHub:
    def __init__(self, existing=True, failure=False, stale=False):
        self.events = []
        self.failure = failure
        self.stale = stale
        self.checks = 0
        self.existing = existing
        self.release = {'id': 10, 'draft': False, 'assets': [
            {'id': 50, 'name': 'openstep-qemu-old.tar.gz'}]} if existing else None
    def api(self, method, path, payload=None, missing=False):
        self.events.append((method, path, payload))
        if path == 'git/ref/heads/master':
            self.checks += 1
            return {'object': {'sha': COMMIT if not self.stale or self.checks == 1 else 'b' * 40}}
        if path.startswith('git/ref/tags/v'):
            return {'object': {'type': 'commit', 'sha': COMMIT}}
        if path == 'git/ref/tags/master-build':
            return {'object': {'type': 'commit', 'sha': COMMIT}} if self.existing else None
        if path.startswith('releases/tags/'):
            return self.release
        if method == 'POST' and path == 'releases':
            return {'id': 10, 'draft': True, 'assets': []}
    def upload(self, tag, path):
        self.events.append(('UPLOAD', path.name, None))
        if self.failure:
            raise RuntimeError('simulated upload failure')
    def asset_matches(self, asset, path):
        return asset.get('digest') == 'sha256:' + release.sha(path)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.candidate = self.root / 'candidate'
        self.sources = {name: release.inputs(name) for name in ('qemu', 'seabios')}
    def tearDown(self):
        self.tmp.cleanup()
    def archives(self, mixed=False, x64=False):
        for index, host in enumerate(release.HOSTS):
            root = version.archive_stem(host, COMMIT)
            system, architecture = host.rsplit('-', 1)
            identity = {'distribution_version': VERSION, 'repository_commit': COMMIT,
                        'sources': self.sources}
            if mixed and index == 3:
                identity['repository_commit'] = 'b' * 40
            build = {**identity, 'platform': system, 'architecture': architecture,
                     'firmware': {'bios_sha256': digest(b'bios'), 'source': self.sources['seabios'],
                                  'config_sha256': release.sha(ROOT / 'configs/seabios.config'),
                                  'extra_version': '-openstep-' + VERSION},
                     'qtests': {'device-test': {'passed': 1, 'exit_code': 0}}}
            ext = '.exe' if system == 'windows' else ''
            files = {root + '/BUILD.json': json.dumps(build).encode(),
                     root + '/bin/qemu-system-i386' + ext: b'emulator',
                     root + '/bin/qemu-img' + ext: b'img',
                     root + '/share/qemu/bios.bin': b'bios',
                     root + '/share/qemu/bios-256k.bin': b'bios'}
            if x64 and index == 0:
                files[root + '/bin/qemu-system-x86_64'] = b'extra'
            hashes = {name.removeprefix(root + '/'): digest(data) for name, data in files.items()}
            files[root + '/SHA256.json'] = json.dumps(hashes).encode()
            if system == 'windows':
                archive = self.artifacts / (root + '.zip')
                with zipfile.ZipFile(archive, 'w') as z:
                    for name, data in files.items():
                        z.writestr(name, data)
            else:
                archive = self.artifacts / (root + '.tar.gz')
                self.tar(archive, files)
            self.sidecar(archive)
            source_files = {'source/SOURCE-BUILD.json': json.dumps(identity).encode()}
            for entry in self.sources.values():
                for item in entry['patch_sha256']:
                    path = entry['patches'] + '/' + item['file']
                    source_files['recipes/' + path] = (ROOT / path).read_bytes()
            archive = self.artifacts / (root + '-source.tar.gz')
            self.tar(archive, source_files)
            self.sidecar(archive)
    def tar(self, path, files):
        with tarfile.open(path, 'w:gz') as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name); info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    def sidecar(self, path):
        path.with_name(path.name + '.sha256').write_text(release.sha(path) + '  ' + path.name + '\n')
    def ready(self):
        self.archives()
        return release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_versions(self):
        base = {'GITHUB_SHA': COMMIT, 'GITHUB_REF': 'refs/heads/master',
                'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'}
        self.assertEqual(version.current_version(base), VERSION)
        self.assertEqual(version.current_version({'GITHUB_REF': 'refs/tags/v1.2.3'}), '1.2.3')
        with self.assertRaises(ValueError):
            version.current_version({'OPENSTEP_VERSION': '../escape\nTOKEN=x'})
    def test_archive_name(self):
        self.assertEqual(version.archive_stem('linux-x86_64', COMMIT),
                         'openstep-qemu-11.1.1-aaaaaaa-linux-x86_64')

    def test_candidate_requires_all_hosts(self):
        self.archives()
        next(self.artifacts.glob('*windows*.zip')).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing host'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
        self.assertFalse(self.candidate.exists())
    def test_candidate_rejects_mixed_commits(self):
        self.archives(mixed=True)
        with self.assertRaisesRegex(ValueError, 'Mixed version/commit'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_candidate_rejects_x64_download(self):
        self.archives(x64=True)
        with self.assertRaisesRegex(ValueError, 'x86_64 emulator'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_candidate_rejects_bad_sidecar(self):
        self.archives()
        next(self.artifacts.glob('*.sha256')).write_text('bad\n')
        with self.assertRaisesRegex(ValueError, 'checksum sidecar'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_source_archive_patch_drift_is_rejected(self):
        self.archives()
        archive = next(self.artifacts.glob('*-source.tar.gz'))
        with tarfile.open(archive) as tar:
            files = {member.name: tar.extractfile(member).read() for member in tar if member.isfile()}
        name = next(name for name in files if name.endswith('.patch'))
        files[name] += b'changed'
        self.tar(archive, files); self.sidecar(archive)
        with self.assertRaisesRegex(ValueError, 'patch drift'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_bundle_bios_manifest_mismatch_is_rejected(self):
        self.archives()
        archive = self.artifacts / (version.archive_stem('linux-x86_64', COMMIT) + '.tar.gz')
        with tarfile.open(archive) as tar:
            files = {member.name: tar.extractfile(member).read() for member in tar if member.isfile()}
        root = version.archive_stem('linux-x86_64', COMMIT)
        files[root + '/share/qemu/bios.bin'] = b'wrong BIOS'
        hashes = {name.removeprefix(root + '/'): digest(data) for name, data in files.items()
                  if not name.endswith('/SHA256.json')}
        files[root + '/SHA256.json'] = json.dumps(hashes).encode()
        self.tar(archive, files); self.sidecar(archive)
        with self.assertRaisesRegex(ValueError, 'BIOS does not match'):
            release.prepare(self.artifacts, self.candidate, VERSION, COMMIT)
    def test_promotion_occurs_after_all_uploads(self):
        self.ready(); api = FakeGitHub()
        release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        actions = [event[0] for event in api.events]
        last_upload = max(i for i, action in enumerate(actions) if action == 'UPLOAD')
        self.assertTrue(all(i > last_upload for i, action in enumerate(actions) if action in ('PATCH', 'DELETE')))
        self.assertEqual(actions.count('UPLOAD'), 4)
    def test_only_four_binary_assets(self):
        manifest = self.ready()
        self.assertEqual(len(manifest['assets']), 4)
        for asset in manifest['assets']:
            self.assertNotIn('-source.', asset['name'])
            self.assertTrue(asset['name'].endswith(('.tar.gz', '.zip')))
        api = FakeGitHub()
        release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        uploads = [event[1] for event in api.events if event[0] == 'UPLOAD']
        self.assertEqual(set(uploads), {asset['name'] for asset in manifest['assets']})

    def test_upload_failure_preserves_old_release(self):
        self.ready(); api = FakeGitHub(failure=True)
        with self.assertRaisesRegex(RuntimeError, 'upload failure'):
            release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        self.assertFalse(any(event[0] in ('PATCH', 'DELETE') for event in api.events))
    def test_master_advancing_preserves_old_release(self):
        self.ready(); api = FakeGitHub(stale=True)
        release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        self.assertFalse(any(event[0] in ('PATCH', 'DELETE') for event in api.events))
    def test_first_master_release_creates_ref_after_uploads(self):
        self.ready(); api = FakeGitHub(existing=False)
        release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        create = next(i for i, event in enumerate(api.events) if event[:2] == ('POST', 'git/refs'))
        self.assertTrue(all(i < create for i, event in enumerate(api.events) if event[0] == 'UPLOAD'))
    def test_tampered_candidate_never_calls_github(self):
        self.ready(); api = FakeGitHub()
        next(self.candidate.glob('*.tar.gz')).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'candidate changed'):
            release.publish(self.candidate, VERSION, COMMIT, 'master-build', api)
        self.assertEqual(api.events, [])
    def test_versioned_release_is_not_overwritten(self):
        self.ready(); api = FakeGitHub()
        with self.assertRaisesRegex(ValueError, 'already-published'):
            release.publish(self.candidate, VERSION, COMMIT, 'v' + VERSION, api)
        self.assertFalse(any(event[0] in ('UPLOAD', 'PATCH', 'DELETE') for event in api.events))

if __name__ == '__main__':
    unittest.main()
