import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('vm_install', Path(__file__).resolve().parents[1] / 'scripts/vm-install.py')
vmi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vmi)


class GuestCommandSyntax(unittest.TestCase):
    def test_guest_commands_parse_as_bash(self):
        for name in ('SETUP', 'INSTALL', 'SERIAL_SETUP', 'POWER_OFF', 'VERIFY'):
            with self.subTest(command=name):
                command = getattr(vmi, name)
                self.assertTrue(command.endswith('\n'), f'{name} must submit with a newline')
                result = subprocess.run(['bash', '-n'], input=command, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_setup_and_disk_markers_are_newline_framed(self):
        for text, marker in ((vmi.SETUP, b'GUEST_READY'),
                             (vmi.INSTALL, b'INSTALL_DONE'), (vmi.SERIAL_SETUP, b'SERIAL_SETUP_DONE'),
                             (vmi.POWER_OFF, b'UMOUNTED')):
            self.assertIn(f"printf '\\n{marker.decode()}\\n'".encode(), text.encode())

    def test_uefi_disk_boot_retains_firmware_without_live_iso(self):
        with patch.object(Path, 'is_file', return_value=True):
            command = vmi.qemu_command('disk.img', 'serial.sock', mode='uefi', variables='vars.fd')
        self.assertTrue(any('OVMF_CODE_4M.fd' in value for value in command))
        self.assertTrue(any('vars.fd' in value for value in command))
        self.assertNotIn('-cdrom', command)

    def test_bios_boot_does_not_require_uefi_firmware(self):
        command = vmi.qemu_command('disk.img', 'serial.sock', mode='bios')
        self.assertFalse(any('pflash' in value for value in command))

    def test_serial_setup_enables_console_and_getty(self):
        self.assertIn(b'console=ttyS0,115200', vmi.SERIAL_SETUP.encode())
        self.assertIn(b'systemctl enable serial-getty@ttyS0.service', vmi.SERIAL_SETUP.encode())
        self.assertIn(b'GRUB_CMDLINE_LINUX_DEFAULT=', vmi.SERIAL_SETUP.encode())


class VerificationCommand(unittest.TestCase):
    def run_verify(self, service_status=0, guide_present=False):
        mocks = '''test() { return 0; }
sleep() { return 0; }
systemctl() { if [[ $1 == is-active ]]; then echo %s; return %s; fi; return 0; }
grep() { case "$*" in *ravnux-vm*) return 0;; esac; command grep "$@"; }
export -f test sleep systemctl grep
''' % ('active' if service_status == 0 else 'activating', service_status)
        if guide_present:
            mocks += "test() { case \"$*\" in '! -e /usr/local/bin/ravnux-guide') return 1;; *) return 0;; esac; }; export -f test\n"
        return subprocess.run(['bash', '-c', mocks + vmi.VERIFY], capture_output=True, text=True)

    def test_pass_marker_prints_after_successful_checks(self):
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('RAVNUX_INSTALL_OK', result.stdout)
        self.assertNotIn('RAVNUX_VM_FAIL', result.stdout)

    def test_guide_left_on_disk_fails_verification(self):
        result = self.run_verify(guide_present=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RAVNUX_VM_FAIL', result.stdout)
        self.assertNotIn('RAVNUX_INSTALL_OK', result.stdout)

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
