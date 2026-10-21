#!/usr/bin/env python3
"""Check platform-specific stripping before bundle dependency signing."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

scripts = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location('package_tools', scripts / 'package.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class DebugStripping(unittest.TestCase):
    def test_platform_flags(self):
        for host, option in [('macos', '-S'), ('linux', '--strip-debug'),
                             ('windows', '--strip-debug')]:
            with self.subTest(host=host), mock.patch.object(package.subprocess, 'run') as run:
                package.strip_debug(Path('binary'), host)
                run.assert_called_once_with(['strip', option, 'binary'], check=True)


if __name__ == '__main__':
    unittest.main()
