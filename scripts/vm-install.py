#!/usr/bin/env python3
"""Install RAVNUX onto a blank disk inside BIOS/UEFI VMs through the interactive wizard, then boot from that disk."""
import argparse
import base64
import importlib.util
import os
from pathlib import Path
import shutil
import shlex
import socket
import subprocess
import tempfile
import textwrap
import time

spec = importlib.util.spec_from_file_location('vm_smoke', Path(__file__).with_name('vm-smoke.py'))
vm_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm_smoke)
SerialConsole = vm_smoke.SerialConsole
qmp_spec = importlib.util.spec_from_file_location('vm_qmp', Path(__file__).with_name('vm-qmp.py'))
vm_qmp = importlib.util.module_from_spec(qmp_spec)
qmp_spec.loader.exec_module(vm_qmp)

HOSTNAME = 'ravnux-vm'
USERNAME = 'tester'
PASSWORD = 'ravnux-test'

# The ERR trap marker matches the one SerialConsole.expect treats as a failure.
SETUP = '''stty -echo; set -euo pipefail; trap 'printf "\\nRAVNUX_VM_FAIL\\n" >&2' ERR; printf '\\nGUEST_READY\\n'
'''
INSTALL = '''ravnux-install; printf '\\nINSTALL_DONE\\n'
'''
# Serial console instrumentation on the installed system: the shipped image has none,
# and headless verification needs kernel output plus a getty on ttyS0.
# Appending the variable again is safe: grub-mkconfig sources the file, last value wins.
SERIAL_SETUP = '''arch-chroot /mnt /bin/bash -c "echo 'GRUB_CMDLINE_LINUX_DEFAULT=\\"loglevel=3 console=tty0 console=ttyS0,115200\\"' >> /etc/default/grub; grub-mkconfig -o /boot/grub/grub.cfg; systemctl enable serial-getty@ttyS0.service"; printf '\\nSERIAL_SETUP_DONE\\n'
'''
POWER_OFF = '''sync; umount -R /mnt || { echo 'umount /mnt failed; holders:'; grep ' /mnt' /proc/self/mountinfo || true; printf '\\nRAVNUX_VM_FAIL\\n'; exit 1; }; printf '\\nUMOUNTED\\n'; poweroff
'''
# Single-quoted for Fish: the whole payload must reach bash -c unexpanded.
VERIFY = '''bash -c 'trap "printf \\"\\nRAVNUX_VM_FAIL\\n\\"" ERR; set -e; grep -qx {hostname} /etc/hostname; for i in $(seq 1 120); do if systemctl is-active lightdm 2>/dev/null | grep -qx active; then break; fi; sleep 1; done; for service in NetworkManager lightdm; do systemctl is-active "$service"; done; test -s /usr/share/pixmaps/ravnux-logo.png; test ! -e /usr/share/ravnux/guide-pl.md; test ! -e /usr/local/bin/ravnux-guide; test ! -e /usr/share/applications/ravnux-guide.desktop; test ! -e /usr/local/bin/ravnux-setup; test ! -e /usr/local/bin/ravnux-install; printf "\\nRAVNUX_INSTALL_OK\\n"'
'''.format(hostname=HOSTNAME)

MANUAL_GREETER = '''if grep -R -E "^[[:space:]]*autologin-user[[:space:]]*=" /mnt/etc/lightdm; then false; fi
printf '[Seat:*]\\ngreeter-hide-users=true\\n' > /mnt/etc/lightdm/lightdm.conf.d/99-ravnux-ci-manual-user.conf
'''

GRAPHICAL_VERIFY = '''bash -c 'set -e; trap "printf \\"\\nRAVNUX_VM_FAIL\\n\\"" ERR; export XDG_RUNTIME_DIR=/run/user/$(id -u) DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus; for i in $(seq 1 90); do if pgrep -u "$USER" -x xfce4-session >/dev/null; then break; fi; sleep 1; done; pgrep -u "$USER" -x xfce4-session; xrandr --query; test "$(xfconf-query -c xsettings -p /Net/ThemeName)" = RAVNUX; test "$(xfconf-query -c xsettings -p /Net/IconThemeName)" = RAVNUX; wallpaper_ready=0; for attempt in {1..40}; do if xfconf-query -c xfce4-desktop -lv | grep -F /usr/share/backgrounds/ravnux/cyberpunk-city.jpg >/dev/null; then wallpaper_ready=1; break; fi; sleep 0.5; done; xfconf-query -c xfce4-desktop -lv; test "$wallpaper_ready" = 1; test "$(xfconf-query -c xfce4-terminal -p /color-foreground)" = "#a6f28a"; test "$(pgrep -u "$USER" -f ^/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 | wc -l)" -eq 1; wpctl status; pavucontrol >/tmp/ravnux-audio-client.log 2>&1 & mixer_pid=$!; for service in pipewire.service pipewire-pulse.service wireplumber.service; do  for attempt in {1..30}; do if systemctl --user is-active --quiet "$service"; then break; fi; sleep 1; done;  systemctl --user is-active "$service"; done; wpctl status; kill "$mixer_pid"; wait "$mixer_pid" || true;  if sudo -n true; then false; fi; printf "\\nRAVNUX_GRAPHICAL_OK\\n"'
'''

ROOT_PRODUCTION_CHECKS = '''echo RAVNUX_PRODUCTION_INSTALLED_HEALTH
timeout 90 systemctl is-system-running --wait || true
systemctl --failed --no-pager
journalctl -b -p err --no-pager -n 80 || true
failed_units=$(systemctl --failed --no-legend --plain)
test -z "$failed_units"
test "$(passwd -S root | awk '{print $2}')" = L
if getent passwd ravnux; then false; fi
id tester
id -nG tester | tr ' ' '\\n' | grep -Fx wheel
if sudo -l -U tester | grep NOPASSWD; then false; fi
test "$(stat -c %u /tmp/ravnux-polkit-ok)" = 0
rm /tmp/ravnux-polkit-ok
visudo -cf /etc/sudoers
findmnt --verify --verbose
pacman -Qk linux grub lightdm xfce4-session
getent ahostsv4 archlinux.org
pacman -Syu --noconfirm
# Reinstallation exercises real filesystem/OS branding and kernel initramfs hooks.
pacman -S --noconfirm filesystem linux
. /etc/os-release
test "$ID" = ravnux
test -s /boot/vmlinuz-linux
test -s /boot/initramfs-linux.img
grub-script-check /boot/grub/grub.cfg
printf '\\nRAVNUX_PRODUCTION_OK\\n'
'''


def qemu_command(disk, serial, iso=None, mode="bios", variables=None, disk_bus="virtio"):
    command = ['qemu-system-x86_64', '-m', '3072', '-smp', '2',
               '-display', 'none', '-serial', f'unix:{serial},server=on,wait=off',
               '-qmp', f'unix:{serial}.qmp,server=on,wait=off',
               '-nic', 'user,model=virtio-net-pci', '-no-reboot',
                   '-audiodev', 'none,id=audio0', '-device', 'intel-hda',
                   '-device', 'hda-duplex,audiodev=audio0']
    if disk_bus == 'virtio':
        command += ['-drive', f'file={disk},if=virtio,format=raw']
    elif disk_bus == 'sata':
        command += ['-drive', f'file={disk},if=none,id=systemdisk,format=raw',
                    '-device', 'ich9-ahci,id=sata', '-device', 'ide-hd,drive=systemdisk,bus=sata.0']
    elif disk_bus == 'nvme':
        command += ['-drive', f'file={disk},if=none,id=systemdisk,format=raw',
                    '-device', 'nvme,drive=systemdisk,serial=RAVNUX-CI']
    else:
        raise ValueError(f'Unsupported disk bus: {disk_bus}')
    if mode == 'uefi':
        code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        if not code.is_file() or variables is None:
            raise RuntimeError('UEFI install tests require ovmf firmware and writable variables')
        command += ['-drive', f'if=pflash,format=raw,readonly=on,file={code}',
                    '-drive', f'if=pflash,format=raw,file={variables}']
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
    try:
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
    except BaseException:
        connection.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise
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


def user_probe(body, marker):
    script = 'set -euo pipefail; trap \'printf "\\nRAVNUX_VM_FAIL\\n"\' ERR; '
    script += body + '; printf "\\n' + marker + '\\n"'
    return 'bash -c ' + shlex.quote(script) + '\n'



def window_probe(pattern):
    return '''export DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority";
ready=0;
for attempt in {1..40}; do
 window=$(xprop -root _NET_ACTIVE_WINDOW | awk 'match($0, /0x[0-9a-fA-F]+/) {print substr($0, RSTART, RLENGTH)}');
 if [[ $window =~ ^0x[0-9a-fA-F]+$ && $window != 0x0 ]] && xprop -id "$window" WM_CLASS | grep -iE ''' + shlex.quote(pattern) + ''' >/dev/null; then ready=1; break; fi;
 sleep 1;
done;
if [[ $ready == 0 ]]; then xprop -root _NET_ACTIVE_WINDOW; xprop -id "$window" WM_CLASS || true; fi;
test "$ready" = 1'''


def wait_window(console, connection, pattern, marker):
    connection.sendall(user_probe(window_probe(pattern), marker).encode())
    console.expect(('\r\n' + marker + '\r\n').encode(), timeout=60)


def verify_wallpaper_screenshot(path):
    """Check rendered pixels, not just xfconf (which can disagree at login)."""
    from PIL import Image, ImageChops, ImageOps, ImageStat
    reference = Path(__file__).resolve().parents[1] / 'overlay/common/usr/share/backgrounds/ravnux/cyberpunk-city.jpg'
    with Image.open(path) as screenshot, Image.open(reference) as wallpaper:
        actual = screenshot.convert('RGB')
        expected = ImageOps.fit(wallpaper.convert('RGB'), actual.size)
        width, height = actual.size
        # The test terminal and authentication dialog leave this area clear.
        box = (int(width * .8), int(height * .2), width, int(height * .9))
        error = sum(ImageStat.Stat(ImageChops.difference(actual.crop(box), expected.crop(box))).mean) / 3
        if error > 12:
            raise RuntimeError(f'Rendered wallpaper differs from RAVNUX reference: mean error {error:.2f}')


def graphical_login(console, connection, monitor, out, prefix):
    qmp = vm_qmp.QMPClient(monitor)
    try:
        time.sleep(3)
        qmp.screenshot(out / f'vm-install-{prefix}-greeter.png')
        # The test-only drop-in shows a username field. PAM, the greeter and
        # session startup are the real installed components; no autologin.
        qmp.type_text(USERNAME + '\n')
        time.sleep(1)
        qmp.type_text(PASSWORD + '\n')
        time.sleep(3)
        connection.sendall(GRAPHICAL_VERIFY.encode())
        console.expect(b'\r\nRAVNUX_GRAPHICAL_OK\r\n', timeout=120)
        # Launch through XFWM/Appfinder so the process belongs to the
        # authenticated LightDM session. DISPLAY alone does not move a process
        # from the serial login session into the graphical Polkit session.
        terminal_script = '#!/bin/bash\nexport PROMPT_COMMAND="touch /tmp/ravnux-ci-terminal-ready"\nexec bash --noprofile --norc -i\n'
        prepare = 'rm -f /tmp/ravnux-ci-terminal-ready; printf %s ' + shlex.quote(terminal_script)
        prepare += ' > /tmp/ravnux-ci-terminal; chmod 0700 /tmp/ravnux-ci-terminal'
        connection.sendall(user_probe(prepare, 'RAVNUX_TERMINAL_PREPARED').encode())
        console.expect(b'\r\nRAVNUX_TERMINAL_PREPARED\r\n', timeout=30)
        qmp.press('alt', 'f2')
        wait_window(console, connection, 'xfce4-appfinder', 'RAVNUX_APPFINDER_READY')
        qmp.press('ctrl', 'a')
        qmp.type_text('xfce4-terminal --disable-server --title=RAVNUX-AUDIT --execute /tmp/ravnux-ci-terminal\n')
        wait_window(console, connection, 'xfce4-terminal', 'RAVNUX_TERMINAL_WINDOW')
        connection.sendall(user_probe('for attempt in {1..30}; do if test -f /tmp/ravnux-ci-terminal-ready; then break; fi; sleep 1; done; test -f /tmp/ravnux-ci-terminal-ready', 'RAVNUX_TERMINAL_READY').encode())
        console.expect(b'\r\nRAVNUX_TERMINAL_READY\r\n', timeout=45)
        qmp.type_text('pkexec --disable-internal-agent /usr/bin/touch /tmp/ravnux-polkit-ok\n')
        wait_window(console, connection, 'polkit', 'RAVNUX_AUTHORIZATION_READY')
        qmp.screenshot(out / f'vm-install-{prefix}-authorization.png')
        qmp.type_text(PASSWORD + '\n')
        time.sleep(2)
        connection.sendall(user_probe('for attempt in {1..15}; do if test -f /tmp/ravnux-polkit-ok; then break; fi; sleep 1; done; test -f /tmp/ravnux-polkit-ok', 'RAVNUX_POLKIT_OK').encode())
        console.expect(b'\r\nRAVNUX_POLKIT_OK\r\n', timeout=45)
        qmp.type_text('xfce4-screensaver-command --lock\n')
        time.sleep(2)
        check = 'export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus; xfce4-screensaver-command --query; '
        connection.sendall(user_probe(check + 'gdbus call --session --dest org.xfce.ScreenSaver --object-path /org/xfce/ScreenSaver --method org.xfce.ScreenSaver.GetActive | grep -F true', 'RAVNUX_LOCKED').encode())
        console.expect(b'\r\nRAVNUX_LOCKED\r\n', timeout=30)
        # Wake a blank lock screen and clear the entry before entering the
        # password. The wake key must not become part of the credential.
        qmp.press('spc')
        time.sleep(2)
        connection.sendall(user_probe(check + 'gdbus call --session --dest org.xfce.ScreenSaver --object-path /org/xfce/ScreenSaver --method org.xfce.ScreenSaver.GetActive | grep -F true', 'RAVNUX_STILL_LOCKED').encode())
        console.expect(b'\r\nRAVNUX_STILL_LOCKED\r\n', timeout=30)
        qmp.press('ctrl', 'a')
        qmp.press('backspace')
        qmp.type_text(PASSWORD + '\n')
        time.sleep(2)
        connection.sendall(user_probe(check + 'gdbus call --session --dest org.xfce.ScreenSaver --object-path /org/xfce/ScreenSaver --method org.xfce.ScreenSaver.GetActive | grep -F false', 'RAVNUX_UNLOCKED').encode())
        console.expect(b'\r\nRAVNUX_UNLOCKED\r\n', timeout=30)
        qmp.screenshot(out / f'vm-install-{prefix}-desktop.png')
        verify_wallpaper_screenshot(out / f'vm-install-{prefix}-desktop.png')
    except BaseException:
        path = out / f'vm-install-{prefix}-failure.png'
        try:
            qmp.screenshot(path)
            print('RAVNUX_FAILURE_PNG_BASE64_BEGIN', flush=True)
            print('\n'.join(textwrap.wrap(base64.b64encode(path.read_bytes()).decode(), 120)), flush=True)
            print('RAVNUX_FAILURE_PNG_BASE64_END', flush=True)
        except Exception as error:
            print(f'Could not capture failure screenshot: {error}', flush=True)
        # The guest journal and process state are the only way to tell a
        # missed-notification race in xfdesktop from a missing helper or
        # file; capture them whenever a graphical check fails.
        try:
            connection.sendall(user_probe(
                'pgrep -a xfdesktop || echo no-xfdesktop; '
                'journalctl --user -b --no-pager | tail -40 || true',
                'RAVNUX_FAILURE_DIAG').encode())
            console.expect(b'\r\nRAVNUX_FAILURE_DIAG\r\n', timeout=60)
        except Exception as error:
            print(f'Could not capture guest diagnostics: {error}', flush=True)
        raise
    finally:
        qmp.close()


def install(iso, out, timeout, mode, production_checks=False):
    with tempfile.TemporaryDirectory(prefix='ravnux-install-') as directory:
        directory = Path(directory)
        disk = directory / 'disk.img'
        with disk.open('wb') as image:
            image.truncate(36 * 1024 ** 3)

        variables = None
        if mode == 'uefi':
            variables = directory / 'vars.fd'
            shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', variables)

        disk_bus = ('nvme' if mode == 'uefi' else 'sata') if production_checks else 'virtio'
        device = {'virtio': '/dev/vda', 'sata': '/dev/sda', 'nvme': '/dev/nvme0n1'}[disk_bus]
        partition = device + ('p' if disk_bus == 'nvme' else '')
        print(f'Test disk: {disk_bus} ({device})', flush=True)
        print('phase 1: boot the ISO and run ravnux-install', flush=True)
        command = qemu_command(disk, directory / 'live.sock', iso, mode, variables, disk_bus=disk_bus)
        process, console, connection = start_vm(command, directory / 'live.sock',
                                                out / f'vm-install-{mode}-live-qemu.log', timeout)
        try:
            console.expect(b'login:')
            connection.sendall(b'ravnux\n')
            console.expect('❯ '.encode())
            connection.sendall(b'exec sudo bash --noprofile --norc +i\n')
            # sudo flushes pending tty input while starting the root session.
            console.expect(b'# ')
            connection.sendall(SETUP.encode())
            console.expect(b'\r\nGUEST_READY\r\n')
            connection.sendall(b'nm-online -q --timeout=90; curl -fsSI --retry 3 --retry-delay 2 --retry-all-errors --max-time 20 https://archlinux.org >/dev/null; printf \'\\nRAVNUX_NETWORK_READY\\n\'\n')
            console.expect(b'\r\nRAVNUX_NETWORK_READY\r\n', timeout=180)
            connection.sendall(INSTALL.encode())
            console.expect(b'Target whole disk')
            connection.sendall((device + '\n').encode())
            console.expect(b'Computer name')
            connection.sendall(HOSTNAME.encode() + b'\n')
            console.expect(b'Username (root and ravnux are reserved)')
            connection.sendall(USERNAME.encode() + b'\n')
            console.expect(b'Timezone')
            connection.sendall(b'Europe/Warsaw\n')
            console.expect(f'Type ERASE {device} to continue'.encode())
            connection.sendall(f'ERASE {device}\n'.encode())
            console.expect(b'Type INSTALL to continue:')
            connection.sendall(b'INSTALL\n')
            console.expect(b'New password:')
            connection.sendall(PASSWORD.encode() + b'\n')
            console.expect(b'Retype new password:')
            connection.sendall(PASSWORD.encode() + b'\n')
            console.expect(b'Restart now?')
            connection.sendall(b'n\n')
            console.expect(b'\r\nINSTALL_DONE\r\n')
            print('phase 1: ravnux-install finished', flush=True)
            remount = f'mount {partition}2 /mnt; '
            if mode == 'uefi':
                remount += f'mount {partition}1 /mnt/boot/efi; '
            connection.sendall((remount + (MANUAL_GREETER if production_checks else '') + SERIAL_SETUP).encode())
            console.expect(b'\r\nSERIAL_SETUP_DONE\r\n')
            connection.sendall(POWER_OFF.encode())
            console.expect(b'\r\nUMOUNTED\r\n')
        except BaseException:
            print(console.data.decode(errors='replace')[-30000:], flush=True)
            raise
        finally:
            stop_vm(process, console, connection, out, f'{mode}-live', seconds=30)
        if process.returncode != 0:
            raise RuntimeError(f'live VM exited with code {process.returncode}')

        for boot_number in range(2 if production_checks else 1):
            prefix = f'{mode}-disk' + ('-after-upgrade' if boot_number else '')
            print(f'phase 2: boot from installed disk ({prefix})', flush=True)
            serial = directory / f'disk-{boot_number}.sock'
            command = qemu_command(disk, serial, mode=mode, variables=variables, disk_bus=disk_bus)
            process, console, connection = start_vm(command, serial,
                                                    out / f'vm-install-{prefix}-qemu.log', min(timeout, 900))
            try:
                console.expect(b'login:')
                connection.sendall(USERNAME.encode() + b'\n')
                console.expect(b'Password:')
                connection.sendall(PASSWORD.encode() + b'\n')
                console.expect('❯ '.encode())
                # Fish redraws entered commands even with the tty ECHO bit off.
                # The default Fish login was verified above; use a quiet Bash
                # for serial probes so echoed sudo text cannot mimic a prompt.
                connection.sendall(b"exec bash --noprofile --norc\n")
                console.expect(b'$ ', timeout=30)
                connection.sendall(b"stty -echo; printf '\\nRAVNUX_DISK_READY\\n'\n")
                console.expect(b'\r\nRAVNUX_DISK_READY\r\n', timeout=30)
                connection.sendall(VERIFY.encode())
                console.expect(b'\r\nRAVNUX_INSTALL_OK\r\n')
                if production_checks:
                    graphical_login(console, connection, str(serial) + '.qmp', out, prefix)
                    # sudo must authenticate the installed wheel user; no test-only
                    # NOPASSWD rule is added to the target.
                    connection.sendall(b"sudo -k; sudo -p 'RAVNUX_SUDO_PASSWORD: ' bash --noprofile --norc\n")
                    console.expect(b'RAVNUX_SUDO_PASSWORD: ', timeout=30)
                    connection.sendall(PASSWORD.encode() + b'\n')
                    console.expect(b'# ', timeout=60)
                    connection.sendall(SETUP.encode())
                    console.expect(b'\r\nGUEST_READY\r\n')
                    if boot_number == 0:
                        connection.sendall(ROOT_PRODUCTION_CHECKS.encode())
                        console.expect(b'\r\nRAVNUX_PRODUCTION_OK\r\n')
                        connection.sendall(b"sync; printf '\\nRAVNUX_UPGRADE_POWEROFF\\n'; poweroff\n")
                        console.expect(b'\r\nRAVNUX_UPGRADE_POWEROFF\r\n')
                    else:
                        connection.sendall(b"set -e; test -z \"$(systemctl --failed --no-legend --plain)\"; printf '\\nRAVNUX_POST_UPGRADE_OK\\n'\n")
                        console.expect(b'\r\nRAVNUX_POST_UPGRADE_OK\r\n')
            except BaseException:
                print(console.data[-30000:].decode('utf-8', 'replace'), flush=True)
                raise
            finally:
                stop_vm(process, console, connection, out, prefix,
                        seconds=30 if production_checks and boot_number == 0 else 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path)
    parser.add_argument('--output', type=Path, default=Path('out'))
    parser.add_argument('--mode', choices=('bios', 'uefi', 'both'), default='both')
    parser.add_argument('--timeout', type=int, default=3600)
    parser.add_argument('--production-checks', action='store_true',
                        help='Test real GUI authentication, Polkit, lock/unlock, audio and reboot after package reinstallation')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = args.output / 'VM-INSTALL-TESTS.txt'
    report.unlink(missing_ok=True)
    if not args.iso.is_file() or args.timeout <= 0:
        parser.error('Existing ISO and positive timeout required')
    if not shutil.which('qemu-system-x86_64'):
        parser.error('qemu-system-x86_64 is required')
    modes = ('bios', 'uefi') if args.mode == 'both' else (args.mode,)
    for mode in modes:
        print(f'Testing {mode.upper()} interactive installation', flush=True)
        install(args.iso.resolve(), args.output, args.timeout, mode, production_checks=args.production_checks)
    report.write_text(
        f'PASS: {", ".join(modes).upper()} CLI wizard install onto a blank disk; boot from disk; login as {USERNAME}; '
        'NetworkManager and LightDM active; hostname set; bundled logo present; live guide and installers absent.\n'
        'Test instrumentation: serial console kernel arguments and serial-getty@ttyS0 '
        'were enabled on the installed system after installation, for headless verification only.\n' +
        ('Production checks: graphical LightDM login, one Polkit agent, real graphical Polkit authorization, '
         'screen lock/unlock, audio services, password-required sudo, service health, package reinstallation '
         'and a second disk boot with graphical login. The test-only greeter drop-in shows a manual username field.\n'
         if args.production_checks else '') +
        'Not covered: physical hardware, encryption/LVM, dual boot.\n')


if __name__ == '__main__':
    main()
