import importlib.util
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('vm_smoke', Path(__file__).resolve().parents[1] / 'scripts/vm-smoke.py')
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


class SerialChecks(unittest.TestCase):
    def console(self, chunks, timeout=1):
        connection = Mock()
        connection.recv.side_effect = chunks
        process = Mock()
        process.poll.return_value = None
        return vm.SerialConsole(connection, process, timeout)

    def test_multiple_prompts_in_one_chunk_are_preserved(self):
        console = self.console([b'login: prompt ready'])
        for pattern in (b'login:', b'prompt', b'ready'):
            console.expect(pattern)
        self.assertEqual(console.connection.recv.call_count, 1)

    def test_split_marker_and_socket_timeout(self):
        console = self.console([socket.timeout(), b'RAVNUX_', b'VM_OK'])
        console.expect(b'RAVNUX_VM_OK')

    def test_closed_connection_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            self.console([b'']).expect(b'OK')

    def test_timeout_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'did not receive'):
            self.console([], timeout=-1).expect(b'OK')

    def test_guest_failure_fails_immediately(self):
        with self.assertRaisesRegex(RuntimeError, 'Guest validation failed'):
            self.console([b'\r\nRAVNUX_VM_FAIL\r\n']).expect(b'\r\nRAVNUX_VM_OK\r\n')


class GuestChecks(unittest.TestCase):
    def test_previous_pass_report_removed_before_invalid_run(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'VM-TESTS.txt'
            report.write_text('old PASS')
            result = subprocess.run(['python3', str(Path(vm.__file__)),
                str(Path(directory) / 'missing.iso'), '--output', directory], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report.exists())

    def run_guest(self, unexpected='', service_status=0):
        mocks = '''pgrep() { return 0; }
test() { return 0; }
sleep() { return 0; }
sudo() { return 0; }
pacman() { case "$2" in xorg-server|xf86-input-libinput) [[ "$2" == "%s" ]];; *) return 0;; esac; }
systemctl() { return %s; }
''' % (unexpected, service_status)
        return subprocess.run(['bash', '-c', mocks + vm.GUEST_SCRIPT], capture_output=True, text=True)

    def test_success_marker_only_after_checks_pass(self):
        result = self.run_guest()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('RAVNUX_VM_OK', result.stdout)

    def test_unexpected_xorg_server_or_input_fails(self):
        for package in ('xorg-server', 'xf86-input-libinput'):
            with self.subTest(package=package):
                result = self.run_guest(unexpected=package)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('RAVNUX_VM_OK', result.stdout)
                self.assertIn('RAVNUX_VM_FAIL', result.stdout)

    def test_service_failure_never_prints_success(self):
        result = self.run_guest(service_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('RAVNUX_VM_OK', result.stdout)
        self.assertIn('RAVNUX_VM_FAIL', result.stdout)
