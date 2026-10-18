"""Execute the workflow's real publication shell with an isolated fake GitHub CLI."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleasePublication(unittest.TestCase):
    def publish(self, fail_upload=False, corrupt=False, empty=False, production=True):
        workflow = (ROOT / '.github/workflows/iso.yml').read_text()
        body = workflow.split('      - name: Publish ISO to the public releases repository\n')[1]
        script = textwrap.dedent(body.split('        run: |\n', 1)[1].split('  desktop-preview:\n')[0])
        substitutions = {'inputs.vm_tests': 'true', 'inputs.install_test': 'true',
                         'inputs.production_audit': str(production).lower(),
                         'steps.vm.outcome': 'success', 'steps.install.outcome': 'success'}
        script = re.sub(r'\$\{\{\s*(.*?)\s*\}\}',
                        lambda match: substitutions.get(match[1].strip(), 'passed'), script)
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            (tmp / 'out').mkdir()
            binary = tmp / 'bin'
            binary.mkdir()
            iso = tmp / 'out/test.iso'
            iso.write_bytes(b'' if empty else b'ISO fixture')
            checksum = '0' * 64 if corrupt else hashlib.sha256(iso.read_bytes()).hexdigest()
            (tmp / 'out/SHA256SUMS').write_text(checksum + '  ./test.iso\n')
            (tmp / 'out/build-info.txt').write_text('SOURCE_DATE_EPOCH=1792310400\n')
            calls = tmp / 'calls'
            cli = binary / 'gh'
            cli.write_text(f'#!{sys.executable}\n' + '''import json,os,sys
with open(os.environ['CALLS'], 'a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:3] == ['release','upload'] and os.environ['FAIL_UPLOAD'] == '1':
    sys.exit(1)
''')
            cli.chmod(0o755)
            date = binary / 'date'
            date.write_text('#!/bin/sh\necho 2026.10.18\n')
            date.chmod(0o755)
            if not shutil.which('sha256sum'):
                command = binary / 'sha256sum'
                command.write_text('#!/bin/sh\nexec /usr/bin/shasum -a 256 "$@"\n')
                command.chmod(0o755)
            result = subprocess.run(['bash', '-c', script], cwd=tmp, text=True, capture_output=True,
                                    env=dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'],
                                             CALLS=str(calls), FAIL_UPLOAD=str(int(fail_upload)),
                                             RELEASE_REPO='fixture/releases', GITHUB_SHA='a' * 40,
                                             GITHUB_RUN_NUMBER='999'))
            return result, [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []

    def test_only_publish_after_all_uploads_finish(self):
        result, calls = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[0][:2], ['release', 'create'])
        self.assertIn('--draft', calls[0])
        self.assertIn('--latest=false', calls[0])
        self.assertTrue(all(call[:2] == ['release', 'upload'] for call in calls[1:-1]))
        self.assertEqual(calls[-1][:2], ['release', 'edit'])
        self.assertIn('--draft=false', calls[-1])
        self.assertIn('--latest=true', calls[-1])

    def test_failed_upload_keeps_the_release_private(self):
        result, calls = self.publish(fail_upload=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--draft', calls[0])
        self.assertFalse(any(call[:2] == ['release', 'edit'] for call in calls))

    def test_corrupt_or_empty_iso_never_creates_a_release(self):
        for values in ({'corrupt': True}, {'empty': True}):
            with self.subTest(values=values):
                result, calls = self.publish(**values)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])

    def test_without_production_checks_release_is_prerelease(self):
        result, calls = self.publish(production=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--prerelease=true', calls[-1])
        self.assertIn('--latest=false', calls[-1])
