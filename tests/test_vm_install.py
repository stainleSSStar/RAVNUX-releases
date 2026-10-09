import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('vm_install', Path(__file__).resolve().parents[1] / 'scripts/vm-install.py')
vmi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vmi)


class GuestCommandSyntax(unittest.TestCase):
    def test_guest_commands_parse_as_bash(self):
        for name in ('SETUP', 'DISK_PREP', 'INSTALL', 'SERIAL_SETUP', 'POWER_OFF', 'VERIFY'):
            with self.subTest(command=name):
                command = getattr(vmi, name)
                self.assertTrue(command.endswith('\n'), f'{name} must submit with a newline')
                result = subprocess.run(['bash', '-n'], input=command, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_setup_and_disk_markers_are_newline_framed(self):
        for text, marker in ((vmi.SETUP, b'GUEST_READY'), (vmi.DISK_PREP, b'DISK_READY'),
                             (vmi.INSTALL, b'INSTALL_DONE'), (vmi.SERIAL_SETUP, b'SERIAL_SETUP_DONE'),
                             (vmi.POWER_OFF, b'UMOUNTED')):
            self.assertIn(f"printf '\\n{marker.decode()}\\n'".encode(), text.encode())

    def test_serial_setup_enables_console_and_getty(self):
        self.assertIn(b'console=ttyS0,115200', vmi.SERIAL_SETUP.encode())
        self.assertIn(b'systemctl enable serial-getty@ttyS0.service', vmi.SERIAL_SETUP.encode())
        self.assertIn(b'GRUB_CMDLINE_LINUX_DEFAULT=', vmi.SERIAL_SETUP.encode())


class VerificationCommand(unittest.TestCase):
    def run_verify(self, service_status=0):
        mocks = '''test() { return 0; }
sleep() { return 0; }
systemctl() { if [[ $1 == is-active ]]; then echo %s; return %s; fi; return 0; }
export -f test sleep systemctl
''' % ('active' if service_status == 0 else 'activating', service_status)
        return subprocess.run(['bash', '-c', mocks + vmi.VERIFY], capture_output=True, text=True)

    def test_pass_marker_prints_after_successful_checks(self):
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('RAVNUX_INSTALL_OK', result.stdout)
        self.assertNotIn('RAVNUX_VM_FAIL', result.stdout)

    def test_inactive_service_prints_failure_marker(self):
        result = self.run_verify(service_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RAVNUX_VM_FAIL', result.stdout)
        self.assertNotIn('RAVNUX_INSTALL_OK', result.stdout)


class ReportHandling(unittest.TestCase):
    def test_previous_report_removed_and_invalid_run_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'VM-INSTALL-TESTS.txt'
            report.write_text('old PASS')
            result = subprocess.run(['python3', str(Path(vmi.__file__)),
                str(Path(directory) / 'missing.iso'), '--output', directory], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report.exists())
