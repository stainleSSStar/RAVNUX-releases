"""Reject existing accounts before either installer can write to a disk."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UsernameValidation(unittest.TestCase):
    def validate(self, script, username, exists):
        source = (ROOT / 'scripts' / script).read_text()
        if script == 'install.sh':
            source = source.split("target=/mnt hostname=''")[0]
        else:
            source = source.split('if [[ ${BASH_SOURCE[0]}')[0]
        # getent is mocked so tests never depend on the host's account database.
        body = source + f'\ngetent() {{ return {0 if exists else 2}; }}\nvalidate_username "$1"\n'
        return subprocess.run(['bash', '-s', '--', username], input=body,
                              capture_output=True, text=True)

    def test_system_account_is_rejected_in_both_entry_points(self):
        for script in ('install.sh', 'install-wizard.sh'):
            with self.subTest(script=script):
                result = self.validate(script, 'daemon', exists=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Username already exists', result.stderr)

    def test_new_account_is_allowed_in_both_entry_points(self):
        for script in ('install.sh', 'install-wizard.sh'):
            with self.subTest(script=script):
                result = self.validate(script, 'newuser', exists=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_reserved_and_invalid_names_are_always_rejected(self):
        for script in ('install.sh', 'install-wizard.sh'):
            for username in ('root', 'ravnux', '-bad', 'a;reboot', ''):
                with self.subTest(script=script, username=username):
                    self.assertNotEqual(self.validate(script, username, exists=False).returncode, 0)
