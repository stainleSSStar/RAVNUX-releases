#!/usr/bin/env python3
"""Small QEMU monitor client for real keyboard input and guest screenshots."""
import json
from pathlib import Path
import socket
import time


class QMPClient:
    def __init__(self, path, timeout=30):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(1)
        self.deadline = time.monotonic() + timeout
        self.buffer = bytearray()
        self.request_id = 0
        try:
            self.socket.connect(str(path))
            if 'QMP' not in self._read():
                raise RuntimeError('Missing QMP greeting')
            self.command('qmp_capabilities')
        except BaseException:
            self.socket.close()
            raise

    def close(self):
        self.socket.close()

    def _read(self):
        while b'\n' not in self.buffer:
            if time.monotonic() >= self.deadline:
                raise RuntimeError('QMP response timeout')
            try:
                chunk = self.socket.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise RuntimeError('QMP connection closed')
            self.buffer.extend(chunk)
        line, _, remainder = self.buffer.partition(b'\n')
        self.buffer = bytearray(remainder)
        return json.loads(line)

    def command(self, name, arguments=None):
        self.deadline = time.monotonic() + 30
        self.request_id += 1
        self.socket.sendall(json.dumps({'execute': name, 'arguments': arguments or {},
                                      'id': self.request_id}).encode() + b'\n')
        while True:
            response = self._read()
            if response.get('id') != self.request_id:
                continue  # asynchronous QMP events are not command replies
            if 'error' in response:
                raise RuntimeError(f'QMP {name}: {response["error"]}')
            return response.get('return')

    def press(self, *codes):
        self.command('send-key', {'keys': [{'type': 'qcode', 'data': code} for code in codes],
                                  'hold-time': 50})
        time.sleep(0.08)

    def type_text(self, text):
        plain = {' ': 'spc', '-': 'minus', '.': 'dot', '/': 'slash', '\n': 'ret',
                 '\t': 'tab', '=': 'equal', "'": 'apostrophe', ';': 'semicolon',
                 '[': 'bracket_left', ']': 'bracket_right', '\\': 'backslash', ',': 'comma'}
        shifted = {'_': 'minus', ':': 'semicolon', '"': 'apostrophe', '|': 'backslash',
                   '$': '4', '(': '9', ')': '0', '+': 'equal', '!': '1'}
        for char in text:
            if char in shifted:
                self.press('shift', shifted[char])
            elif char.isascii() and char.isupper():
                self.press('shift', char.lower())
            elif char.isascii() and char.isalnum():
                self.press(char)
            elif char in plain:
                self.press(plain[char])
            else:
                raise ValueError(f'Unsupported QEMU test keystroke: {char!r}')

    def screenshot(self, path):
        from PIL import Image
        path = Path(path).resolve()
        ppm = path.with_suffix('.ppm')
        self.command('screendump', {'filename': str(ppm)})
        try:
            with Image.open(ppm) as image:
                image.save(path)
        finally:
            ppm.unlink(missing_ok=True)
