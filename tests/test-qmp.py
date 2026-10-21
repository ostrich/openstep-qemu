#!/usr/bin/env python3
"""Check that each short-lived QMP request releases its connection."""
import concurrent.futures
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / 'risc'))
from risc_control import Guest


class QMPConnections(unittest.TestCase):
    def test_full_backlog_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = mock.Mock()
            connection.gettimeout.return_value = .5
            connection.connect.side_effect = [BlockingIOError(), BlockingIOError(), None]
            Guest(directory)._connect(connection, 'qmp.sock')
            self.assertEqual(connection.connect.call_count, 3)

    def test_backlog_retry_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = mock.Mock()
            connection.gettimeout.return_value = .01
            connection.connect.side_effect = BlockingIOError()
            with self.assertRaises(BlockingIOError):
                Guest(directory)._connect(connection, 'qmp.sock')

    def test_connection_closed_on_success_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(Path(directory) / 'qmp.sock'))
                server.listen(1)
                server.settimeout(3)

                def serve():
                    for fail in (False, True) * 16:
                        connection, _ = server.accept()
                        with connection:
                            connection.settimeout(3)
                            with connection.makefile('rwb') as stream:
                                def send(value):
                                    stream.write(json.dumps(value).encode() + b'\n')
                                    stream.flush()
                                send({'QMP': {}})
                                self.assertEqual(json.loads(stream.readline())['execute'],
                                                 'qmp_capabilities')
                                send({'return': {}})
                                self.assertEqual(json.loads(stream.readline())['execute'],
                                                 'query-status')
                                send({'error': {'desc': 'test error'}} if fail else
                                     {'return': {'status': 'paused'}})
                                self.assertEqual(stream.read(1), b'',
                                                 'Client retained its QMP connection')

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pending = pool.submit(serve)
                    guest = Guest(directory)
                    errors = []  # Keep tracebacks alive, as a concurrent runner can.
                    for _ in range(16):
                        self.assertEqual(guest.qmp('query-status'), {'status': 'paused'})
                        try:
                            guest.qmp('query-status')
                        except RuntimeError as error:
                            errors.append(error)
                        else:
                            self.fail('Expected the test QMP error')
                    pending.result(timeout=5)


if __name__ == '__main__':
    unittest.main()
