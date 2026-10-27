import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'overlay/common/usr/local/bin/ravnux-keyring-init'
FINGERPRINT = '0C92313001CFCA27627B9098B97F7C613F359424'

@unittest.skipUnless(os.geteuid() == 0, 'Keyring helper runs as root')
class SigningKeyValidation(unittest.TestCase):
    def exercise(self, fingerprint, target=None, gpg_status=0, import_status=0):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            fake_gpg = directory / 'gpg'
            fake_gpg.write_text('#!/bin/sh\nprintf "fpr:::::::::%s:\\n" "$TEST_FINGERPRINT"\nexit "$TEST_GPG_STATUS"\n')
            fake_pacman_key = directory / 'pacman-key'
            fake_pacman_key.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\ncase " $* " in *" --add "*) exit "$TEST_IMPORT_STATUS" ;; esac\n')
            fake_gpg.chmod(0o755)
            fake_pacman_key.chmod(0o755)
            log = directory / 'calls'
            env = dict(os.environ, PATH=f'{directory}:{os.environ["PATH"]}',
                       TEST_FINGERPRINT=fingerprint, TEST_LOG=str(log),
                       TEST_GPG_STATUS=str(gpg_status), TEST_IMPORT_STATUS=str(import_status))
            command = ['bash', str(SCRIPT), '/test/signing-key.asc']
            if target:
                command.append(target)
            result = subprocess.run(command,
                                    env=env, text=True, capture_output=True)
            return result, log.read_text().splitlines() if log.exists() else []

    def test_wrong_fingerprint_never_imports_or_trusts_key(self):
        result, calls = self.exercise('0' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('fingerprint mismatch', result.stderr)
        self.assertEqual(calls, [])

    def test_expected_key_is_imported_then_locally_signed(self):
        result, calls = self.exercise(FINGERPRINT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ['--add /test/signing-key.asc', f'--lsign-key {FINGERPRINT}'])

    def test_expected_key_can_seed_a_separate_target_keyring(self):
        result, calls = self.exercise(FINGERPRINT, '/mnt/etc/pacman.d/gnupg')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            '--gpgdir /mnt/etc/pacman.d/gnupg --add /test/signing-key.asc',
            f'--gpgdir /mnt/etc/pacman.d/gnupg --lsign-key {FINGERPRINT}',
        ])

    def test_gpg_failure_never_imports_or_trusts_key(self):
        result, calls = self.exercise(FINGERPRINT, gpg_status=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])

    def test_failed_import_never_signs_key(self):
        result, calls = self.exercise(FINGERPRINT, import_status=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, ['--add /test/signing-key.asc'])
