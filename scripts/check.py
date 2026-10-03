#!/usr/bin/env python3
"""Validate source structure; optionally also validate the assembled Archiso profile."""
from pathlib import Path
import configparser
import re
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
for path in list((root / 'scripts').glob('*.sh')) + list((root / 'overlay').rglob('*')):
    if path.is_file() and path.read_bytes().startswith(b'#!/usr/bin/env bash'):
        subprocess.run(['bash', '-n', str(path)], check=True)
for path in (root / 'overlay').rglob('*.xml'):
    ET.parse(path)
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
assert {'fish', 'pipewire-pulse', 'wireplumber', 'linux-firmware', 'sof-firmware', 'xfce4-session', 'networkmanager'} <= set(system)
assert not (root / 'overlay/common/etc/sudoers.d/10-ravnux-live').exists()
assert not (root / 'overlay/common/etc/lightdm/lightdm.conf.d/50-ravnux-live.conf').exists()
assert not (root / 'overlay/common/etc/passwd').exists()
# Installer must validate arguments and mount before invoking pacstrap.
script = (root / 'scripts/install.sh').read_text()
assert script.index('mountpoint -q') < script.index('pacstrap -C')
assert script.index('confirmation == INSTALL') < script.index('pacstrap -C')
assert not re.search(r'\b(mkfs|wipefs|sgdisk)\b', script)
artwork = {
    'usr/share/pixmaps/ravnux-logo.png': b'\x89PNG\r\n\x1a\n',
    'usr/share/backgrounds/ravnux/cyberpunk-city.jpg': b'\xff\xd8\xff',
}
for path, magic in artwork.items():
    assert (root / 'overlay/common' / path).read_bytes().startswith(magic), path
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
    assert (profile / 'airootfs/usr/share/ravnux/root-overlay/usr/share/ravnux/guide-pl.md').read_text() == guide
    for path in artwork:
        source = (root / 'overlay/common' / path).read_bytes()
        assert (profile / 'airootfs' / path).read_bytes() == source, path
        assert (profile / 'airootfs/usr/share/ravnux/root-overlay' / path).read_bytes() == source, path
print('RAVNUX source checks passed' + ('; assembled profile checked' if profile.exists() else ''))
