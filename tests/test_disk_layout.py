"""Format only freshly allocated loop images; never select a host disk."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

WIZARD = Path(__file__).resolve().parents[1] / 'scripts/install-wizard.sh'
TOOLS = ('losetup', 'parted', 'partprobe', 'mkfs.fat', 'mkfs.ext4', 'udevadm', 'blkid', 'findmnt')


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0 and all(shutil.which(x) for x in TOOLS),
                     'Requires Linux root and disk tools; exercised on CI loop images')
class RealDiskLayouts(unittest.TestCase):
    def exercise_layout(self, mode):
        with tempfile.TemporaryDirectory(prefix='ravnux-loop-test-') as directory:
            directory = Path(directory)
            image = directory / 'blank.img'
            with image.open('wb') as stream:
                stream.truncate(36 * 1024 ** 3)
            target = directory / 'mount'
            target.mkdir()
            disk = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(image)], text=True).strip()
            try:
                result = subprocess.run(['bash', '-c', '''source "$WIZARD_SOURCE"
# Production guards reject loop devices. The fixture permits only this exact
# loop device, which losetup has just allocated against our temporary blank file.
validate_disk() { [[ $1 == "$LOOP_DEVICE" && $1 == /dev/loop* ]] || fail 'Not the fixture loop device'; }
prepare_disk "$LOOP_DEVICE" "$BOOT_MODE" "$TEST_TARGET"
'''], env=dict(os.environ, WIZARD_SOURCE=str(WIZARD), LOOP_DEVICE=disk,
              BOOT_MODE=mode, TEST_TARGET=str(target)), text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                layout = subprocess.check_output(['parted', '-sm', disk, 'print'], text=True)
                self.assertIn(':gpt:', layout)
                self.assertIn('esp' if mode == 'uefi' else 'bios_grub', layout)
                self.assertEqual(subprocess.check_output(['blkid', '-s', 'TYPE', '-o', 'value', disk + 'p2'], text=True).strip(), 'ext4')
                root_source = subprocess.check_output(['findmnt', '-n', '-M', str(target), '-o', 'SOURCE'], text=True).strip()
                self.assertEqual(root_source, disk + 'p2')
                if mode == 'uefi':
                    self.assertEqual(subprocess.check_output(['blkid', '-s', 'TYPE', '-o', 'value', disk + 'p1'], text=True).strip(), 'vfat')
                    esp_source = subprocess.check_output(['findmnt', '-n', '-M', str(target / 'boot/efi'), '-o', 'SOURCE'], text=True).strip()
                    self.assertEqual(esp_source, disk + 'p1')
                else:
                    self.assertFalse((target / 'boot/efi').exists())
                    result = subprocess.run(['blkid', '-s', 'TYPE', '-o', 'value', disk + 'p1'], text=True, capture_output=True)
                    self.assertEqual(result.stdout, '')
            finally:
                subprocess.run(['umount', '-R', str(target)], capture_output=True)
                subprocess.run(['losetup', '--detach', disk], check=True)

    def test_real_uefi_partition_format_and_mount(self):
        self.exercise_layout('uefi')

    def test_real_bios_partition_format_and_mount(self):
        self.exercise_layout('bios')
