#!/usr/bin/env python3
"""Check cleanup races without weakening the SPARC probe assertions."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

root = Path(__file__).resolve().parent / 'risc'
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('pte', root / 'test-microsparc-pte.py')
pte = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pte)


class ProbeCleanup(unittest.TestCase):
    def test_exit_races_quit(self):
        for error in (ConnectionRefusedError(), BlockingIOError(), ValueError()):
            with self.subTest(error=type(error).__name__):
                process = mock.Mock()
                process.poll.return_value = None
                process.wait.return_value = -6
                guest = mock.Mock()
                guest.qmp.side_effect = error
                pte.finish_guest(guest, process)
                process.wait.assert_called_once_with(timeout=3)
                process.kill.assert_not_called()

    def test_already_exited(self):
        process = mock.Mock()
        process.poll.return_value = -6
        guest = mock.Mock()
        pte.finish_guest(guest, process)
        guest.qmp.assert_not_called()
        process.wait.assert_called_once_with(timeout=3)

    def test_unresponsive_probe_fails_and_is_reaped(self):
        process = mock.Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('probe', 3), -9]
        guest = mock.Mock()
        guest.qmp.side_effect = ConnectionRefusedError()
        with self.assertRaisesRegex(RuntimeError, 'did not exit'):
            pte.finish_guest(guest, process)
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)


if __name__ == '__main__':
    unittest.main()
