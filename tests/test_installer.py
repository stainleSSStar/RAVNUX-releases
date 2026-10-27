import subprocess
import os
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / 'scripts/install.sh'

class InstallerPreflight(unittest.TestCase):
    def run_installer(self, *args):
        return subprocess.run(['bash', str(INSTALLER), *args], text=True, capture_output=True)

    def test_help_without_target(self):
        result = self.run_installer('--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Does not partition or format', result.stdout)

    def test_missing_option_value(self):
        result = self.run_installer('--hostname')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing value', result.stderr)

    def test_unknown_option(self):
        result = self.run_installer('--erase-disk')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown option', result.stderr)

    def test_root_target_is_rejected_before_install(self):
        result = self.run_installer('--hostname', 'ravpc', '--username', 'tester', '--target', '/')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Target must be', result.stderr)

    def test_invalid_user_and_hostname(self):
        for args in [('--hostname', '-bad', '--username', 'tester'),
                     ('--hostname', 'good', '--username', 'root'),
                     ('--hostname', 'good', '--username', 'a;reboot')]:
            with self.subTest(args=args):
                result = self.run_installer(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Invalid', result.stderr)

    def test_timezone_traversal_is_rejected(self):
        result = self.run_installer('--hostname', 'ravpc', '--username', 'tester', '--timezone', '../etc/passwd')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid timezone', result.stderr)

    def exercise_target(self, relative=None, error=None, find_failure=False, symlink=False):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            target = directory / 'target'
            esp = target / 'boot/efi'
            esp.mkdir(parents=True)
            if relative:
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'keep existing file')
            if symlink:
                esp.rmdir()
                esp.symlink_to(directory, target_is_directory=True)
            env = os.environ.copy()
            if find_failure:
                command = directory / 'find'
                command.write_text('#!/bin/sh\ncase "$1" in */boot/efi) exit 1;; *) exec /usr/bin/find "$@";; esac\n')
                command.chmod(0o755)
                env['PATH'] = str(directory) + ':' + env['PATH']
            # Execute the installer's actual validation function without disk operations.
            functions = INSTALLER.read_text().split("target=/mnt hostname=''")[0]
            result = subprocess.run(['bash', '-s', '--', str(target)],
                                    input=functions + '\nvalidate_target_files "$1" ""\n',
                                    env=env, text=True, capture_output=True)
            if error:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
            if relative:
                self.assertEqual(path.read_bytes(), b'keep existing file')

    def test_existing_efi_loaders_are_never_overwritten(self):
        for loader in ('EFI/BOOT/BOOTX64.EFI', 'EFI/Microsoft/Boot/bootmgfw.efi', '.hidden'):
            with self.subTest(loader=loader):
                self.exercise_target('boot/efi/' + loader, 'ESP is not empty')

    def test_existing_boot_files_are_never_overwritten(self):
        self.exercise_target('boot/grub/grub.cfg', 'Target boot directory is not empty')

    def test_existing_root_files_are_never_overwritten(self):
        self.exercise_target('etc/os-release', 'Target root is not empty')

    def test_unreadable_esp_is_rejected(self):
        self.exercise_target(error='Cannot inspect ESP', find_failure=True)

    def test_redirected_efi_path_is_rejected(self):
        self.exercise_target(error='Boot paths must not be symbolic links', symlink=True)

    def test_empty_target_passes_file_protection_checks(self):
        self.exercise_target()

if __name__ == '__main__':
    unittest.main()
