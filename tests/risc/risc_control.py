"""Bounded QMP/serial controls for the isolated RISC test guests."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time

class Guest:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def _connect(self, sock, name):
        # These Linux-hosted labs can exceed sockaddr_un's pathname limit.
        # A directory descriptor avoids global chdir and works across threads.
        fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            sock.connect('/proc/self/fd/' + str(fd) + '/' + name)
        finally:
            os.close(fd)

    def qmp(self, command, arguments=None, timeout=5):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            self._connect(sock, 'qmp.sock')
            stream = sock.makefile('rwb')
            json.loads(stream.readline())
            def execute(name, args=None):
                request = {'execute': name}
                if args is not None:
                    request['arguments'] = args
                stream.write(json.dumps(request).encode() + b'\n')
                stream.flush()
                while True:
                    row = json.loads(stream.readline())
                    if 'error' in row:
                        raise RuntimeError(row['error'])
                    if 'return' in row:
                        return row['return']
            execute('qmp_capabilities')
            return execute(command, arguments)

    def key(self, key):
        self.qmp('human-monitor-command', {'command-line': 'sendkey ' + key + ' 50'})
        # Let the emulated keyboard deliver release before another key command.
        time.sleep(.08)

    def serial_line(self, text):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            self._connect(sock, 'serial.sock')
            # The loader can drop characters sent back-to-back through the SCC.
            for value in (text + '\n').encode('ascii'):
                sock.sendall(bytes([value]))
                time.sleep(.2)

    def serial_text(self):
        return (self.directory / 'serial.log').read_text(errors='replace')

    def screen(self, name='current'):
        from PIL import Image
        ppm = self.directory / (name + '.ppm')
        png = self.directory / (name + '.png')
        self.qmp('screendump', {'filename': str(ppm)})
        Image.open(ppm).save(png)
        return png

    def screen_text(self, name='current'):
        result = subprocess.run(['tesseract', str(self.screen(name)), 'stdout'],
                                capture_output=True, text=True, timeout=10, check=True)
        return result.stdout
