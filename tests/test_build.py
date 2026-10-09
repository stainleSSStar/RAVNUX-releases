import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildPreparation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.repo = self.directory / 'repo'
        shutil.copytree(ROOT, self.repo, symlinks=True, ignore=shutil.ignore_patterns(
            'profile', 'out', 'work', '__pycache__', '.git'))
        self.releng = self.directory / 'releng'
        fixtures = {
            'profiledef.sh': 'iso_name=archlinux\nfile_permissions=()\n',
            'airootfs/etc/mkinitcpio.conf.d/archiso.conf': 'HOOKS=(base archiso archiso_pxe_nbd)\n',
            'airootfs/etc/passwd': 'upstream-rescue-user\n',
            'syslinux/archiso_sys-linux.cfg': 'APPEND archisobasedir=%INSTALL_DIR%\n# Accessibility boot option\nLABEL speech\n',
            'efiboot/loader/entries/01-linux.conf': 'title Arch Linux\noptions archisobasedir=%INSTALL_DIR%\n',
            'efiboot/loader/entries/02-speech-linux.conf': 'options accessibility=on\n',
            'grub/grub.cfg': 'linux /vmlinuz archisobasedir=%INSTALL_DIR%\n',
        }
        for name, content in fixtures.items():
            path = self.releng / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def prepare(self, **extra):
        env = dict(os.environ, RAVNUX_RELENG_DIR=str(self.releng),
                   SOURCE_DATE_EPOCH='1791108000', **extra)
        return subprocess.run(['bash', 'scripts/build.sh', '--prepare-only'],
                              cwd=self.repo, env=env, capture_output=True, text=True)

    def test_real_preparation_copies_assets_and_preserves_boot_paths(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        profile = self.repo / 'profile'
        self.assertFalse((profile / 'airootfs/etc/passwd').exists())
        for name in ('syslinux/archiso_sys-linux.cfg', 'efiboot/loader/entries/01-linux.conf', 'grub/grub.cfg'):
            text = (profile / name).read_text()
            self.assertIn('archisobasedir=%INSTALL_DIR%', text)
            self.assertIn('console=tty0 console=ttyS0,115200', text)
            self.assertNotIn('LABEL speech', text)
        self.assertFalse((profile / 'efiboot/loader/entries/02-speech-linux.conf').exists())
        firstboot = profile / 'airootfs/etc/systemd/system/systemd-firstboot.service'
        self.assertTrue(firstboot.is_symlink())
        self.assertEqual(os.readlink(firstboot), '/dev/null')
        for prefix in ('airootfs', 'airootfs/usr/share/ravnux/root-overlay'):
            localtime = profile / prefix / 'etc/localtime'
            self.assertTrue(localtime.is_symlink(), prefix)
            self.assertEqual(os.readlink(localtime), '/usr/share/zoneinfo/Europe/Warsaw')
        source = self.repo / 'overlay/common/usr/share/pixmaps/ravnux-logo.png'
        for prefix in ('airootfs', 'airootfs/usr/share/ravnux/root-overlay'):
            self.assertEqual(source.read_bytes(), (profile / prefix / 'usr/share/pixmaps/ravnux-logo.png').read_bytes())
        metadata = subprocess.run(['bash', '-c',
            'declare -A file_permissions; source profile/profiledef.sh; printf "%s %s" "$iso_label" "$iso_version"'],
            cwd=self.repo, env=dict(os.environ, SOURCE_DATE_EPOCH='1791108000'), capture_output=True, text=True)
        self.assertEqual(metadata.returncode, 0, metadata.stderr)
        self.assertEqual(metadata.stdout, 'RAVNUX_202610 2026.10.04')

    def test_previous_profile_is_not_overwritten(self):
        (self.repo / 'profile').mkdir()
        sentinel = self.repo / 'profile/keep'
        sentinel.write_text('keep')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_dangling_output_symlink_is_rejected(self):
        (self.repo / 'out').symlink_to(self.directory / 'absent')
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertFalse((self.repo / 'profile').exists())

    def test_invalid_epoch_is_rejected_before_writing_profile(self):
        env = dict(os.environ, RAVNUX_RELENG_DIR=str(self.releng), SOURCE_DATE_EPOCH='invalid')
        result = subprocess.run(['bash', 'scripts/build.sh', '--prepare-only'], cwd=self.repo,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid SOURCE_DATE_EPOCH', result.stderr)
        self.assertFalse((self.repo / 'profile').exists())

    def test_incomplete_upstream_is_rejected_before_copying(self):
        (self.releng / 'airootfs/etc/mkinitcpio.conf.d/archiso.conf').unlink()
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing Archiso template', result.stderr)
        self.assertFalse((self.repo / 'profile').exists())
