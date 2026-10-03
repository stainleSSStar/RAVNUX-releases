import subprocess
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

if __name__ == '__main__':
    unittest.main()
