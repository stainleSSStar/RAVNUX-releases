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
for attempt in {1..300}; do
 if pgrep -u ravnux -x xfce4-session >/dev/null && test -S /tmp/.X11-unix/X0; then break; fi
 sleep 1
done
pgrep -u ravnux -x xfce4-session
test -S /tmp/.X11-unix/X0
pgrep -x Xorg || pgrep -x Xlibre
pacman -Q xlibre-xserver xlibre-input-libinput fish pipewire wireplumber
# pacman -Q also resolves provisions, so compare installed names, not providers.
installed="$(pacman -Qq)"
for package in xorg-server xf86-input-libinput; do
 if printf '%s\\n' "$installed" | grep -Fx "$package" >/dev/null; then
  printf 'Unexpected package: %s\\n' "$package" >&2
  false
 fi
done
for service in NetworkManager lightdm; do systemctl is-active "$service"; done
systemctl is-enabled bluetooth
test -s /usr/share/pixmaps/ravnux-logo.png
test -s /usr/share/backgrounds/ravnux/cyberpunk-city.jpg
test -x /usr/local/bin/ravnux-install
test -x /usr/local/bin/ravnux-setup
test -x /usr/local/bin/ravnux-guide
test -s /usr/share/applications/ravnux-guide.desktop
test -s /usr/share/ravnux/guide-pl.md
# sudo flushes pending tty input when it sets up the target session, so nothing
# may follow this line; keep the completion marker in the same line and fail via
# the ERR trap if the display check fails.
if sudo -u ravnux env XDG_RUNTIME_DIR=/run/user/1000 DISPLAY=:0 XAUTHORITY=/home/ravnux/.Xauthority DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus bash -c 'set -e; xdpyinfo >/dev/null; test "$(xfconf-query -c xsettings -p /Net/ThemeName)" = RAVNUX; test "$(xfconf-query -c xfce4-terminal -p /color-foreground)" = "#a6f28a"; test "$(xfconf-query -c xfce4-terminal -p /background-mode)" = TERMINAL_BACKGROUND_TRANSPARENT; test "$(xfconf-query -c xfwm4 -p /general/use_compositing)" = true; for attempt in {1..40}; do if xfconf-query -c xfce4-desktop -lv | grep -F /usr/share/backgrounds/ravnux/cyberpunk-city.jpg >/dev/null; then exit 0; fi; sleep 1; done; exit 1'; then printf '\\nRAVNUX_VM_OK\\n'; else false; fi
'''

PRODUCTION_LIVE_CHECKS = '''
echo RAVNUX_PRODUCTION_LIVE_HEALTH
timeout 90 systemctl is-system-running --wait || true
systemctl --failed --no-pager
journalctl -b -p err --no-pager -n 80 || true
failed_units=$(systemctl --failed --no-legend --plain)
test -z "$failed_units"
ss -lntp
if ss -H -lnt | awk '{print $4}' | grep -E ':(22|6000)$' >/dev/null; then
 echo 'Unexpected SSH or TCP X11 listener' >&2
 false
fi
'''

PRODUCTION_DESKTOP_CHECKS = '''
test "$(pgrep -u ravnux -f ^/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 | wc -l)" -eq 1;
wpctl status; pavucontrol >/tmp/ravnux-audio-client.log 2>&1 & mixer_pid=$!; for service in pipewire.service pipewire-pulse.service wireplumber.service; do  for attempt in {1..30}; do if systemctl --user is-active --quiet "$service"; then break; fi; sleep 1; done;  systemctl --user is-active "$service"; done; wpctl status; kill "$mixer_pid"; wait "$mixer_pid" || true; 
'''.replace('\n', ' ')


def guest_script(production_checks=False):
    if not production_checks:
        return GUEST_SCRIPT
    return GUEST_SCRIPT.replace('# sudo flushes', PRODUCTION_LIVE_CHECKS + '# sudo flushes', 1).replace(
        'xdpyinfo >/dev/null;', 'xdpyinfo >/dev/null; ' + PRODUCTION_DESKTOP_CHECKS, 1)


class SerialConsole:
    def __init__(self, connection, process, timeout):
        self.connection = connection
        self.process = process
        self.deadline = time.monotonic() + timeout
        self.data = bytearray()
        self.cursor = 0

    def expect(self, pattern, timeout=None):
        deadline = self.deadline if timeout is None else min(self.deadline, time.monotonic() + timeout)
        while pattern not in self.data[self.cursor:]:
            if time.monotonic() > deadline or self.process.poll() is not None:
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


def boot(iso, mode, out, timeout=600, allow_kvm=True, production_checks=False):
    with tempfile.TemporaryDirectory(prefix='ravnux-vm-') as directory:
        directory = Path(directory)
        serial = directory / 'serial.sock'
        command = ['qemu-system-x86_64', '-m', '3072', '-smp', '2',
                   '-cdrom', str(iso), '-boot', 'd', '-display', 'none',
                   '-serial', f'unix:{serial},server=on,wait=off',
                   '-nic', 'user,model=virtio-net-pci', '-no-reboot',
                   '-audiodev', 'none,id=audio0', '-device', 'intel-hda',
                   '-device', 'hda-duplex,audiodev=audio0']
        if allow_kvm and os.access('/dev/kvm', os.R_OK | os.W_OK):
            command += ['-machine', 'accel=kvm:tcg']
        else:
            command += ['-machine', 'accel=tcg']
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
                # sudo flushes pending tty input while starting the root session,
                # so the probe must only be sent after the root shell prompt shows.
                console.expect(b'# ')
                connection.sendall(b"stty -echo; printf '\\nRAVNUX_CHECK_READY\\n'\n")
                console.expect(b'\r\nRAVNUX_CHECK_READY\r\n')
                # No encoded payload; echo is disabled so source cannot count as a result.
                connection.sendall(guest_script(production_checks).encode())
                console.expect(b'\r\nRAVNUX_VM_OK\r\n')
                print(f'{mode}: ISO boot, XFCE/XLibre, services and assets passed', flush=True)
            except BaseException:
                print(console.data[-30000:].decode('utf-8', 'replace'), flush=True)
                raise
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
    parser.add_argument('--no-kvm', action='store_true',
                        help='Force TCG even when /dev/kvm is available (e.g. CI runners with unreliable KVM)')
    parser.add_argument('--production-checks', action='store_true',
                        help='Also require healthy system units, one Polkit agent and active audio services')
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
        boot(args.iso.resolve(), mode, args.output, args.timeout, allow_kvm=not args.no_kvm,
             production_checks=args.production_checks)
    (args.output / 'VM-TESTS.txt').write_text(
        f'PASS: {", ".join(modes)} ISO boot; XFCE session; XLibre display; '
        'NetworkManager, LightDM, Bluetooth services; bundled logo, wallpaper and installer.\n'
        'Not covered: installation, physical graphics/audio/Wi-Fi/Bluetooth/USB hardware.\n')


if __name__ == '__main__':
    main()
