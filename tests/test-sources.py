#!/usr/bin/env python3
"""Check patch inventory safety and source-drift detection using small Git fixtures."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('source_tools', ROOT / 'scripts/sources.py')
source_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_tools)

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.previous = source_tools.ROOT
        source_tools.ROOT = self.root
    def tearDown(self):
        source_tools.ROOT = self.previous
        self.tmp.cleanup()
    def inventory(self):
        base = self.root / 'patches/qemu'
        (base / 'topics').mkdir(parents=True)
        name = '0001-test-a.patch'
        (base / name).write_text('Subject: [PATCH 1/1] test: a\n')
        (base / 'series').write_text(name + '\n')
        (base / 'topics/test.series').write_text(name + '\n')
        (self.root / 'upstream.json').write_text(json.dumps({'projects': {'qemu': {
            'url': 'https://example.invalid/source.git', 'version': 'test',
            'revision': 'a' * 40, 'patches': 'patches/qemu', 'topics': ['test']}}}))
        return base
    def test_rejects_unlisted_patch(self):
        base = self.inventory()
        (base / '0002-test-b.patch').write_text('Subject: [PATCH 2/2] test: b\n')
        with self.assertRaisesRegex(ValueError, 'cover every patch'):
            source_tools.inputs('qemu')
    def test_rejects_wrong_subject_and_topic(self):
        base = self.inventory()
        (base / '0001-test-a.patch').write_text('Subject: [PATCH 1/2] test: a\n')
        with self.assertRaisesRegex(ValueError, 'Subject numbering'):
            source_tools.inputs('qemu')
        (base / '0001-test-a.patch').write_text('Subject: [PATCH 1/1] test: a\n')
        (base / 'topics/test.series').write_text('0002-test-b.patch\n')
        with self.assertRaisesRegex(ValueError, 'partition'):
            source_tools.inputs('qemu')
    def test_interleaved_topics_follow_global_order(self):
        base = self.inventory()
        names = [f'{i:04d}-test-{i}.patch' for i in range(1, 4)]
        (base / '0001-test-a.patch').unlink()
        for i, name in enumerate(names, 1):
            (base / name).write_text(f'Subject: [PATCH {i}/3] test: {i}\n')
        (base / 'series').write_text('\n'.join(names) + '\n')
        (base / 'topics/test.series').write_text(names[0] + '\n' + names[2] + '\n')
        (base / 'topics/other.series').write_text(names[1] + '\n')
        manifest = self.root / 'upstream.json'
        data = json.loads(manifest.read_text())
        data['projects']['qemu']['topics'].append('other')
        manifest.write_text(json.dumps(data))
        source_tools.inputs('qemu')
        (base / 'topics/test.series').write_text(names[2] + '\n' + names[0] + '\n')
        with self.assertRaisesRegex(ValueError, 'topic order'):
            source_tools.inputs('qemu')

    def test_rejects_traversal(self):
        base = self.inventory()
        (base / 'series').write_text('../outside.patch\n')
        with self.assertRaises(ValueError):
            source_tools.inputs('qemu')
    def test_detects_worktree_index_and_untracked_drift(self):
        repo = self.root / 'source'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        subprocess.run(['git', 'config', 'user.name', 'fixture'], cwd=repo, check=True)
        subprocess.run(['git', 'config', 'user.email', 'fixture@example.invalid'], cwd=repo, check=True)
        file = repo / 'file'
        file.write_text('original\n')
        subprocess.run(['git', 'add', 'file'], cwd=repo, check=True)
        subprocess.run(['git', 'commit', '-qm', 'fixture'], cwd=repo, check=True)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        file.write_text('patched\n')
        subprocess.run(['git', 'add', 'file'], cwd=repo, check=True)
        expected = {'revision': revision}
        state = {'inputs': expected, 'index_sha256': source_tools.index_digest(repo)}
        source_tools.verify(repo, expected, state)
        file.write_text('modified again\n')
        with self.assertRaises(subprocess.CalledProcessError):
            source_tools.verify(repo, expected, state)
        subprocess.run(['git', 'add', 'file'], cwd=repo, check=True)
        with self.assertRaisesRegex(ValueError, 'Applied source'):
            source_tools.verify(repo, expected, state)
        state['index_sha256'] = source_tools.index_digest(repo)
        (repo / 'unexpected').write_text('preserve me\n')
        with self.assertRaisesRegex(ValueError, 'untracked'):
            source_tools.verify(repo, expected, state)

if __name__ == '__main__':
    unittest.main()
