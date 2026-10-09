#!/usr/bin/env python3
"""Install RAVNUX onto a blank disk inside a VM (BIOS), then boot from that disk."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

spec = importlib.util.spec_from_file_location('vm_smoke', Path(__file__).with_name('vm-smoke.py'))
vm_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm_smoke)
SerialConsole = vm_smoke.SerialConsole

HOSTNAME = 'ravnux-vm'
USERNAME = 'tester'
PASSWORD = 'ravnux-test'

# The ERR trap marker matches the one SerialConsole.expect treats as a failure.
SETUP = '''stty -echo; set -euo pipefail; trap 'printf "\\nRAVNUX_VM_FAIL\\n" >&2' ERR; printf '\\nGUEST_READY\\n'
'''
DISK_PREP = '''parted -s /dev/vda mklabel msdos mkpart primary ext4 1MiB 100%; partprobe -s /dev/vda || true; udevadm settle || true; mkfs.ext4 -F /dev/vda1; udevadm settle || true; mkdir -p /mnt; mount /dev/vda1 /mnt; printf '\\nDISK_READY\\n'
'''
INSTALL = f'''ravnux-install --target /mnt --hostname {HOSTNAME} --username {USERNAME} --bios-disk /dev/vda; printf '\\nINSTALL_DONE\\n'
'''
# Serial console instrumentation on the installed system: the shipped image has none,
# and headless verification needs kernel output plus a getty on ttyS0.
# Appending the variable again is safe: grub-mkconfig sources the file, last value wins.
SERIAL_SETUP = '''arch-chroot /mnt /bin/bash -c "echo 'GRUB_CMDLINE_LINUX_DEFAULT=\\"loglevel=3 console=tty0 console=ttyS0,115200\\"' >> /etc/default/grub; grub-mkconfig -o /boot/grub/grub.cfg; systemctl enable serial-getty@ttyS0.service"; printf '\\nSERIAL_SETUP_DONE\\n'
'''
POWER_OFF = '''sync; umount /mnt || { echo 'umount /mnt failed; holders:'; grep ' /mnt' /proc/self/mountinfo || true; for fd in /proc/[0-9]*/fd/*; do readlink "$fd" 2>/dev/null; done | grep '^/mnt' | sort -u || true; umount -l /mnt; }; printf '\\nUMOUNTED\\n'; poweroff
'''
# Single-quoted for Fish: the whole payload must reach bash -c unexpanded.
VERIFY = '''bash -c 'trap "printf \\"\\nRAVNUX_VM_FAIL\\n\\"" ERR; set -e; grep -qx {hostname} /etc/hostname; for i in $(seq 1 120); do if systemctl is-active lightdm 2>/dev/null | grep -qx active; then break; fi; sleep 1; done; systemctl is-active NetworkManager lightdm; test -x /usr/local/bin/ravnux-install; test -s /usr/share/pixmaps/ravnux-logo.png; printf "\\nRAVNUX_INSTALL_OK\\n"'
'''.format(hostname=HOSTNAME)


def qemu_command(disk, serial, iso=None):
    command = ['qemu-system-x86_64', '-m', '3072', '-smp', '2',
               '-drive', f'file={disk},if=virtio,format=raw',
               '-display', 'none', '-serial', f'unix:{serial},server=on,wait=off',
               '-nic', 'user,model=virtio-net-pci', '-no-reboot']
    if iso is not None:
        command += ['-cdrom', str(iso), '-boot', 'd']
    if os.access('/dev/kvm', os.R_OK | os.W_OK):
        command += ['-machine', 'accel=kvm:tcg']
    else:
        command += ['-machine', 'accel=tcg']
    return command


def start_vm(command, serial, error_path, timeout):
    with error_path.open('wb') as error:
        process = subprocess.Popen(command, stdout=error, stderr=subprocess.STDOUT)
    connection = socket.socket(socket.AF_UNIX)
    console = SerialConsole(connection, process, timeout)
    while True:
        if process.poll() is not None:
            raise RuntimeError(f'QEMU exited early with code {process.returncode}; see {error_path.name}')
        if time.monotonic() > console.deadline:
            raise RuntimeError('QEMU serial socket never appeared')
        try:
            connection.connect(str(serial))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            time.sleep(0.1)
    connection.settimeout(1)
    return process, console, connection


def stop_vm(process, console, connection, out, prefix, seconds):
    try:
        (out / f'vm-install-{prefix}-serial.log').write_bytes(console.data)
    finally:
        connection.close()
        try:
            process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def install(iso, out, timeout):
    with tempfile.TemporaryDirectory(prefix='ravnux-install-') as directory:
        directory = Path(directory)
        disk = directory / 'disk.img'
        with disk.open('wb') as image:
            image.truncate(16 * 1024 ** 3)

        print('phase 1: boot the ISO and run ravnux-install', flush=True)
        command = qemu_command(disk, directory / 'live.sock', iso)
        process, console, connection = start_vm(command, directory / 'live.sock',
                                                out / 'vm-install-live-qemu.log', timeout)
        try:
            console.expect(b'login:')
            connection.sendall(b'ravnux\n')
            console.expect('❯ '.encode())
            connection.sendall(b'exec sudo bash --noprofile --norc +i\n')
            # sudo flushes pending tty input while starting the root session.
            console.expect(b'# ')
            connection.sendall(SETUP.encode())
            console.expect(b'\r\nGUEST_READY\r\n')
            connection.sendall(DISK_PREP.encode())
            console.expect(b'\r\nDISK_READY\r\n')
            connection.sendall(INSTALL.encode())
            console.expect(b'Type INSTALL to continue:')
            connection.sendall(b'INSTALL\n')
            console.expect(b'New password:')
            connection.sendall(PASSWORD.encode() + b'\n')
            console.expect(b'Retype new password:')
            connection.sendall(PASSWORD.encode() + b'\n')
            console.expect(b'\r\nINSTALL_DONE\r\n')
            print('phase 1: ravnux-install finished', flush=True)
            connection.sendall(SERIAL_SETUP.encode())
            console.expect(b'\r\nSERIAL_SETUP_DONE\r\n')
            connection.sendall(POWER_OFF.encode())
            console.expect(b'\r\nUMOUNTED\r\n')
        finally:
            stop_vm(process, console, connection, out, 'live', seconds=30)
        if process.returncode != 0:
            raise RuntimeError(f'live VM exited with code {process.returncode}')

        print('phase 2: boot from the installed disk', flush=True)
        command = qemu_command(disk, directory / 'disk.sock')
        process, console, connection = start_vm(command, directory / 'disk.sock',
                                                out / 'vm-install-disk-qemu.log', min(timeout, 900))
        try:
            console.expect(b'login:')
            connection.sendall(USERNAME.encode() + b'\n')
            console.expect(b'Password:')
            connection.sendall(PASSWORD.encode() + b'\n')
            console.expect('❯ '.encode())
            connection.sendall(VERIFY.encode())
            console.expect(b'\r\nRAVNUX_INSTALL_OK\r\n')
        finally:
            stop_vm(process, console, connection, out, 'disk', seconds=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path)
    parser.add_argument('--output', type=Path, default=Path('out'))
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = args.output / 'VM-INSTALL-TESTS.txt'
    report.unlink(missing_ok=True)
    if not args.iso.is_file() or args.timeout <= 0:
        parser.error('Existing ISO and positive timeout required')
    if not shutil.which('qemu-system-x86_64'):
        parser.error('qemu-system-x86_64 is required')
    install(args.iso.resolve(), args.output, args.timeout)
    report.write_text(
        f'PASS: BIOS install onto a blank disk; boot from disk; login as {USERNAME}; '
        'NetworkManager and LightDM active; installer and logo present.\n'
        'Test instrumentation: serial console kernel arguments and serial-getty@ttyS0 '
        'were enabled on the installed system after installation, for headless verification only.\n'
        'Not covered: UEFI install, physical hardware, encryption/LVM, dual boot.\n')


if __name__ == '__main__':
    main()
