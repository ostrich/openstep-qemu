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
    def test_host_graphics_stay_on_host(self):
        for name in ('libwayland-client.so.0', 'libwayland-cursor.so.0',
                     'libwayland-egl.so.1', 'libgbm.so.1', 'libdrm.so.2',
                     'libdrm_amdgpu.so.1', 'libEGL_mesa.so.0', 'libGLX.so.0',
                     'libGLdispatch.so.0', 'libvulkan.so.1'):
            with self.subTest(name=name):
                self.assertIsNotNone(package.LINUX_HOST_GRAPHICS.fullmatch(name))
        for name in ('libSDL2-2.0.so.0', 'libglib-2.0.so.0', 'libpixman-1.so.0'):
            self.assertIsNone(package.LINUX_HOST_GRAPHICS.fullmatch(name))
        output = ('libwayland-client.so.0 => /lib/libwayland-client.so.0 (0x1)\n'
                  'libgbm.so.1 => /lib/libgbm.so.1 (0x2)\n'
                  'libSDL2-2.0.so.0 => /lib/libSDL2-2.0.so.0 (0x3)\n')
        with mock.patch.object(package.subprocess, 'check_output', return_value=output):
            self.assertEqual(package.dependencies(Path('qemu'), 'linux'),
                             [Path('/lib/libSDL2-2.0.so.0')])

    def test_platform_flags(self):
        for host, option in [('macos', '-S'), ('linux', '--strip-debug'),
                             ('windows', '--strip-debug')]:
            with self.subTest(host=host), mock.patch.object(package.subprocess, 'run') as run:
                package.strip_debug(Path('binary'), host)
                run.assert_called_once_with(['strip', option, 'binary'], check=True)


if __name__ == '__main__':
    unittest.main()
