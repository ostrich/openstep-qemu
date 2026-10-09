#!/usr/bin/env python3
"""Check CI host selection against shared and platform-specific changes."""
import runpy
import unittest
from pathlib import Path

hosts = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/ci-scope.py'))['hosts']


class ScopeTests(unittest.TestCase):
    def test_documentation(self):
        self.assertEqual(hosts(['README.md', 'docs/build.md']), set())

    def test_platform_inputs(self):
        self.assertEqual(hosts(['build/windows.sh', 'launch/openstep.ps1']), {'windows'})
        self.assertEqual(hosts(['build/macos.sh']), {'macos'})
        self.assertEqual(hosts(['launch/openstep.sh']), {'linux', 'macos'})

    def test_shared_inputs(self):
        for path in ['docs/bundle.md', 'build/common.sh', 'upstream.json',
                     'patches/qemu/new.patch', '.github/workflows/build.yml']:
            with self.subTest(path=path):
                self.assertEqual(hosts([path]), {'linux', 'macos', 'windows'})


if __name__ == '__main__':
    unittest.main()
