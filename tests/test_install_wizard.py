"""Exercise disk guards and UEFI/BIOS plans without touching host disks."""
import os
from pathlib import Path
import subprocess
import unittest

WIZARD = Path(__file__).resolve().parents[1] / 'scripts/install-wizard.sh'


class DiskWizard(unittest.TestCase):
    def run_shell(self, body, answer='', **env):
        return subprocess.run(['bash', '-c', 'source "$WIZARD_SOURCE"\n' + body],
                              input=answer, text=True, capture_output=True,
                              env=dict(os.environ, WIZARD_SOURCE=str(WIZARD), **env))

    def validate(self, **env):
        return self.run_shell('''
disk_is_block() { return 0; }
lsblk() {
 case "$*" in
  '-dn -o TYPE '*) echo "${DISK_TYPE:-disk}" ;;
  '-dn -o RO '*) echo "${DISK_RO:-0}" ;;
  '-bdn -o SIZE '*) echo "${DISK_SIZE:-68719476736}" ;;
  '-nr -o MOUNTPOINTS '*) printf '%s\\n' "${DISK_MOUNTS:-}" ;;
  '-nr -o TYPE '*) printf '%s\\n' "${DISK_TYPES:-disk}" ;;
  '-nr -o KNAME '*) echo ravnux-test-nonexistent-device ;;
  *) return 1 ;;
 esac
}
validate_disk /dev/ravnux-test
''', **env)

    def test_unmounted_plain_disk_is_accepted(self):
        self.assertEqual(self.validate(DISK_TYPES='disk\npart').returncode, 0)

    def test_rejects_live_media_swap_readonly_small_and_mapped_disks(self):
        for env, message in (
            ({'DISK_MOUNTS': '/run/archiso/bootmnt'}, 'mounted'),
            ({'DISK_MOUNTS': '[SWAP]'}, 'swap'),
            ({'DISK_RO': '1'}, 'read-only'),
            ({'DISK_SIZE': '1073741824'}, '32 GiB'),
            ({'DISK_SIZE': 'unknown'}, '32 GiB'),
            ({'DISK_TYPE': 'part'}, 'whole disk'),
            ({'DISK_TYPES': 'disk\npart\ncrypt'}, 'encryption'),
            ({'DISK_TYPES': 'disk\npart\nlvm'}, 'LVM'),
        ):
            with self.subTest(env=env):
                result = self.validate(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_mount_inspection_failure_stops_installation(self):
        result = self.run_shell('''
disk_is_block() { return 0; }
lsblk() {
 case "$*" in
  '-dn -o TYPE '*) echo disk ;;
  '-dn -o RO '*) echo 0 ;;
  '-bdn -o SIZE '*) echo 68719476736 ;;
  *) return 1 ;;
 esac
}
validate_disk /dev/ravnux-test
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot inspect mounts', result.stderr)

    def test_requires_exact_disk_specific_erase_confirmation(self):
        for answer in ('y\n', 'ERASE\n', 'ERASE /dev/other\n', '\n'):
            with self.subTest(answer=answer):
                result = self.run_shell('confirm_erase /dev/ravnux-test\necho WRITE_REACHED', answer)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('WRITE_REACHED', result.stdout)
        result = self.run_shell('confirm_erase /dev/ravnux-test\necho CONFIRMED',
                                'ERASE /dev/ravnux-test\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('CONFIRMED', result.stdout)

    def test_partition_names_for_sata_nvme_and_mmc(self):
        for disk, partition in (('/dev/sda', '/dev/sda2'), ('/dev/nvme0n1', '/dev/nvme0n1p2'),
                                ('/dev/mmcblk0', '/dev/mmcblk0p2')):
            result = self.run_shell(f'partition_path {disk} 2')
            self.assertEqual(result.stdout.strip(), partition)

    def partition_plan(self, mode, rejected=False):
        return self.run_shell('''
validate_disk() { echo REVALIDATE; %s; }
parted() { printf 'PARTED %%s\\n' "$*"; }
partprobe() { :; }
udevadm() { :; }
mkfs.fat() { printf 'FAT %%s\\n' "$*"; }
mkfs.ext4() { printf 'EXT4 %%s\\n' "$*"; }
mount() { printf 'MOUNT %%s\\n' "$*"; }
mkdir() { :; }
prepare_disk /dev/nvme0n1 %s
''' % ("fail 'disk became busy'" if rejected else ':', mode))

    def test_uefi_plan_uses_fat_esp_and_ext4_root(self):
        result = self.partition_plan('uefi')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('mklabel gpt', result.stdout)
        self.assertIn('set 1 esp on', result.stdout)
        self.assertIn('FAT -F 32 /dev/nvme0n1p1', result.stdout)
        self.assertIn('EXT4 -F /dev/nvme0n1p2', result.stdout)
        self.assertIn('MOUNT /dev/nvme0n1p1 /mnt/boot/efi', result.stdout)
        self.assertTrue(result.stdout.startswith('REVALIDATE\n'))

    def test_bios_plan_has_unformatted_bios_boot_partition(self):
        result = self.partition_plan('bios')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('set 1 bios_grub on', result.stdout)
        self.assertIn('EXT4 -F /dev/nvme0n1p2', result.stdout)
        self.assertNotIn('FAT ', result.stdout)
        self.assertNotIn('/mnt/boot/efi', result.stdout)

    def test_disk_becoming_busy_prevents_first_write(self):
        result = self.partition_plan('uefi', rejected=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PARTED ', result.stdout)

    def test_help_requires_no_privileges_or_disk(self):
        result = subprocess.run(['bash', str(WIZARD), '--help'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('UEFI/BIOS', result.stdout)

    def test_transient_unmount_failure_is_retried(self):
        result = self.run_shell('''
unmount_calls=0
umount() { unmount_calls=$((unmount_calls + 1)); echo "UNMOUNT $*"; [[ $unmount_calls -ge 2 ]]; }
sleep() { :; }
unmount_target /test/ravnux
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('UNMOUNT -R /test/ravnux'), 2)

    def test_persistent_unmount_failure_is_reported_without_force(self):
        result = self.run_shell('''
umount() { echo "UNMOUNT $*"; return 1; }
sleep() { :; }
findmnt() { return 0; }
readlink() { return 1; }
unmount_target /test/ravnux
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Cannot unmount', result.stderr)
        self.assertEqual(result.stdout.count('UNMOUNT -R /test/ravnux'), 3)
        self.assertNotIn('-l', result.stdout)
        self.assertNotIn('-f', result.stdout)
