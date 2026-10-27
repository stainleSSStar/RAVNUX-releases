#!/usr/bin/env python3
"""Validate source structure; optionally also validate the assembled Archiso profile."""
from pathlib import Path
import configparser
import os
import re
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
for path in list((root / 'scripts').glob('*.sh')) + list((root / 'overlay').rglob('*')):
    if path.is_file() and path.read_bytes().startswith(b'#!/usr/bin/env bash'):
        subprocess.run(['bash', '-n', str(path)], check=True)
for path in list((root / 'overlay').rglob('*.xml')) + list((root / 'overlay').rglob('*.svg')):
    ET.parse(path)
panel = ET.parse(root / 'overlay/common/etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml')
rgba = panel.find('.//property[@name="background-rgba"]')
assert rgba is not None and rgba.get('type') == 'array', 'Panel RGBA must be a boxed array, not a CSS string'
assert len(rgba) == 4 and all(v.get('type') == 'double' and 0 <= float(v.get('value')) <= 1 for v in rgba), \
    'Panel RGBA needs four normalized doubles'
for pattern in ('*.desktop', '*.ini', 'terminalrc', '*.theme'):
    for path in (root / 'overlay').rglob(pattern):
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(path)
system = (root / 'packages/system.txt').read_text().splitlines()
live = (root / 'packages/live.txt').read_text().splitlines()
for packages in (system, live):
    assert len(packages) == len(set(packages)), 'Duplicate packages'
    assert all(re.fullmatch(r'[a-z0-9+_.-]+', p) for p in packages), 'Invalid package name'
assert {'xlibre-xserver', 'xlibre-input-libinput'} <= set(system)
assert not set(system) & {'xorg-server', 'xf86-input-libinput'}
assert '[xlibre-stable]' in (root / 'overlay/common/etc/pacman.conf').read_text()
assert not set(system) & {'firefox', 'chromium', 'archinstall', 'libreoffice-fresh', 'git', 'base-devel'}
assert not set(system) & {'arch-install-scripts', 'mkinitcpio-archiso', 'nano', 'less', 'alsa-utils', 'vulkan-intel', 'vulkan-radeon'}
assert {'fish', 'pipewire-pulse', 'wireplumber', 'linux-firmware', 'sof-firmware', 'xfce4-session', 'networkmanager'} <= set(system)
assert not (root / 'overlay/common/etc/sudoers.d/10-ravnux-live').exists()
assert not (root / 'overlay/common/etc/lightdm/lightdm.conf.d/50-ravnux-live.conf').exists()
assert not (root / 'overlay/common/etc/passwd').exists()
# mkarchiso marks every live image as first boot (uninitialized machine-id);
# the wizard would otherwise block the serial console and tty1 with prompts.
firstboot_mask = root / 'overlay/live/etc/systemd/system/systemd-firstboot.service'
assert firstboot_mask.is_symlink() and os.readlink(firstboot_mask) == '/dev/null', \
    'Live image must mask systemd-firstboot.service'
localtime = root / 'overlay/common/etc/localtime'
assert localtime.is_symlink() and os.readlink(localtime).startswith('/usr/share/zoneinfo/'), \
    'Live image needs a timezone symlink'
assert 'nbd' in live, 'Archiso PXE NBD hook requires nbd-client'
# Installer must validate arguments and mount before invoking pacstrap.
script = (root / 'scripts/install.sh').read_text()
assert script.index('mountpoint -q') < script.index('pacstrap -C')
assert script.index('confirmation == INSTALL') < script.index('pacstrap -C')
assert not re.search(r'\b(mkfs|wipefs|sgdisk)\b', script)
# 'pacman -Q xorg-server' would succeed whenever xlibre-xserver (which provides
# xorg-server) is installed; the installer must compare installed names instead.
assert 'pacman -Qq' in script, 'Installer must check installed names, not provisions'
assert 'pacman -Q xorg-server' not in script, 'Installer queries xorg-server as a provision'
artwork = {
    'usr/share/pixmaps/ravnux-logo.png': b'\x89PNG\r\n\x1a\n',
    'usr/share/backgrounds/ravnux/cyberpunk-city.jpg': b'\xff\xd8\xff',
}
for path, magic in artwork.items():
    assert (root / 'overlay/common' / path).read_bytes().startswith(magic), path
for relative in ('usr/local/bin/ravnux-guide', 'usr/share/applications/ravnux-guide.desktop'):
    assert (root / 'overlay/live' / relative).is_file(), relative
    assert not (root / 'overlay/common' / relative).exists(), relative
guide = (root / 'docs/GUIDE_PL.md').read_text()
for code in re.findall(r'```(?:sh|bash)\n(.*?)```', guide, re.S):
    subprocess.run(['bash', '-n'], input=code, text=True, check=True)
profile = root / 'profile'  
if profile.exists():
    assert set((profile / 'packages.x86_64').read_text().splitlines()) == set(system + live)
    for needed in ('etc/mkinitcpio.conf.d/archiso.conf', 'usr/local/bin/ravnux-install',
                   'usr/share/ravnux/root-overlay/etc/os-release', 'etc/systemd/system/display-manager.service'):
        assert (profile / 'airootfs' / needed).exists() or (profile / 'airootfs' / needed).is_symlink(), needed
    assert not (profile / 'airootfs/etc/systemd/system/multi-user.target.wants/sshd.service').exists()
    assert (profile / 'airootfs/etc/pacman.conf').read_text() == (root / 'overlay/common/etc/pacman.conf').read_text()
    assert (profile / 'airootfs/usr/share/ravnux/guide-pl.md').read_text() == guide
    for relative in ('usr/share/ravnux/guide-pl.md', 'usr/local/bin/ravnux-guide',
                     'usr/share/applications/ravnux-guide.desktop', 'usr/local/bin/ravnux-setup',
                     'usr/local/bin/ravnux-install'):
        assert (profile / 'airootfs' / relative).exists(), relative
        assert not (profile / 'airootfs/usr/share/ravnux/root-overlay' / relative).exists(), relative
    for path in artwork:
        source = (root / 'overlay/common' / path).read_bytes()
        assert (profile / 'airootfs' / path).read_bytes() == source, path
        assert (profile / 'airootfs/usr/share/ravnux/root-overlay' / path).read_bytes() == source, path
    hook = (profile / 'airootfs/etc/mkinitcpio.conf.d/archiso.conf').read_text()
    if 'archiso_pxe_nbd' in hook:
        assert 'nbd' in (profile / 'packages.x86_64').read_text().splitlines()
    serial = profile / 'airootfs/etc/systemd/system/serial-getty@ttyS0.service.d/10-live-setup.conf'
    assert 'After=ravnux-live-setup.service' in serial.read_text()
    assert 'Requires=ravnux-live-setup.service' in serial.read_text()
    firstboot = profile / 'airootfs/etc/systemd/system/systemd-firstboot.service'
    assert firstboot.is_symlink() and os.readlink(firstboot) == '/dev/null', \
        'Prepared profile must keep the firstboot mask a symlink'
    for prefix in ('airootfs', 'airootfs/usr/share/ravnux/root-overlay'):
        link = profile / prefix / 'etc/localtime'
        assert link.is_symlink() and os.readlink(link) == os.readlink(localtime), prefix
    for directory in ('syslinux', 'efiboot', 'grub'):
        for path in (profile / directory).rglob('*'):
            if path.suffix in ('.cfg', '.conf'):
                for line in path.read_text().splitlines():
                    if 'archisobasedir=' in line and not line.lstrip().startswith('#'):
                        assert 'console=tty0 console=ttyS0,115200' in line, path
print('RAVNUX source checks passed' + ('; assembled profile checked' if profile.exists() else ''))
