#!/usr/bin/env python3
"""Boot the real ISO under BIOS and UEFI; exercise the live graphical session."""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


GUEST_SCRIPT = '''set -euo pipefail
trap 'printf "\\nRAVNUX_VM_FAIL\\n"' ERR
for attempt in {1..60}; do
 if pgrep -u ravnux -x xfce4-session >/dev/null && test -S /tmp/.X11-unix/X0; then break; fi
 sleep 1
done
pgrep -u ravnux -x xfce4-session
test -S /tmp/.X11-unix/X0
pgrep -x Xorg || pgrep -x Xlibre
pacman -Q xlibre-xserver xlibre-input-libinput fish pipewire wireplumber
for package in xorg-server xf86-input-libinput; do
 if pacman -Q "$package" >/dev/null 2>&1; then
  printf 'Unexpected package: %s\\n' "$package" >&2
  false
 fi
done
systemctl is-active NetworkManager lightdm
systemctl is-enabled bluetooth
test -s /usr/share/pixmaps/ravnux-logo.png
test -s /usr/share/backgrounds/ravnux/cyberpunk-city.jpg
test -x /usr/local/bin/ravnux-install
test -s /usr/share/ravnux/guide-pl.md
sudo -u ravnux env DISPLAY=:0 XAUTHORITY=/home/ravnux/.Xauthority xdpyinfo >/dev/null
printf '\\nRAVNUX_VM_OK\\n'
'''


class SerialConsole:
    def __init__(self, connection, process, timeout):
        self.connection = connection
        self.process = process
        self.deadline = time.monotonic() + timeout
        self.data = bytearray()
        self.cursor = 0

    def expect(self, pattern):
        while pattern not in self.data[self.cursor:]:
            if time.monotonic() > self.deadline or self.process.poll() is not None:
                raise RuntimeError(f'Serial console did not receive {pattern!r}')
            try:
                chunk = self.connection.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise RuntimeError('Serial console closed')
            self.data.extend(chunk)
            if b'\r\nRAVNUX_VM_FAIL\r\n' in self.data[self.cursor:]:
                raise RuntimeError('Guest validation failed')
        self.cursor = self.data.index(pattern, self.cursor) + len(pattern)


def boot(iso, mode, out, timeout=600):
    with tempfile.TemporaryDirectory(prefix='ravnux-vm-') as directory:
        directory = Path(directory)
        serial = directory / 'serial.sock'
        command = ['qemu-system-x86_64', '-m', '3072', '-smp', '2',
                   '-cdrom', str(iso), '-boot', 'd', '-display', 'none',
                   '-serial', f'unix:{serial},server=on,wait=off',
                   '-nic', 'user,model=virtio-net-pci', '-no-reboot']
        command += ['-accel', 'kvm:tcg' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg']
        if mode == 'uefi':
            code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
            variables = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
            if not code.exists() or not variables.exists():
                raise RuntimeError('Install ovmf with the non-Secure-Boot 4M firmware')
            target_vars = directory / 'vars.fd'
            shutil.copyfile(variables, target_vars)
            command += ['-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                        '-drive', f'if=pflash,format=raw,file={target_vars}']
        error_path = out / f'vm-{mode}-qemu.log'
        with error_path.open('wb') as error:
            process = subprocess.Popen(command, stdout=error, stderr=error)
            connection = socket.socket(socket.AF_UNIX)
            console = SerialConsole(connection, process, timeout)
            try:
                while True:
                    if process.poll() is not None:
                        qemu_output = error_path.read_bytes()[-4000:].decode('utf-8', 'replace')
                        raise RuntimeError(f'{mode}: QEMU failed to start\nQEMU output:\n{qemu_output}')
                    if time.monotonic() > console.deadline:
                        raise RuntimeError(f'{mode}: QEMU failed to start')
                    try:
                        connection.connect(str(serial))
                        break
                    except (FileNotFoundError, ConnectionRefusedError):
                        time.sleep(0.1)
                connection.settimeout(1)
                console.expect(b'login:')
                connection.sendall(b'ravnux\n')
                # login starts Fish; wait for its prompt before injecting the check.
                console.expect('❯ '.encode())
                connection.sendall(b'exec sudo bash --noprofile --norc +i\n')
                connection.sendall(b"stty -echo; printf '\\nRAVNUX_CHECK_READY\\n'\n")
                console.expect(b'\r\nRAVNUX_CHECK_READY\r\n')
                # No encoded payload; echo is disabled so source cannot count as a result.
                connection.sendall(GUEST_SCRIPT.encode())
                console.expect(b'\r\nRAVNUX_VM_OK\r\n')
                print(f'{mode}: ISO boot, XFCE/XLibre, services and assets passed', flush=True)
            finally:
                connection.close()
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                (out / f'vm-{mode}-serial.log').write_bytes(console.data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path)
    parser.add_argument('--output', type=Path, default=Path('out'))
    parser.add_argument('--mode', choices=('bios', 'uefi', 'both'), default='both')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = args.output / 'VM-TESTS.txt'
    report.unlink(missing_ok=True)
    if not args.iso.is_file() or args.timeout <= 0:
        parser.error('Existing ISO and positive timeout required')
    if not shutil.which('qemu-system-x86_64'):
        parser.error('qemu-system-x86_64 is required')
    modes = ('bios', 'uefi') if args.mode == 'both' else (args.mode,)
    for mode in modes:
        boot(args.iso.resolve(), mode, args.output, args.timeout)
    (args.output / 'VM-TESTS.txt').write_text(
        f'PASS: {", ".join(modes)} ISO boot; XFCE session; XLibre display; '
        'NetworkManager, LightDM, Bluetooth services; bundled logo, wallpaper and installer.\n'
        'Not covered: installation, physical graphics/audio/Wi-Fi/Bluetooth/USB hardware.\n')


if __name__ == '__main__':
    main()
