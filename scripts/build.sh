#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
prepare_only=false
if (($#)); then
 [[ $# == 1 && $1 == --prepare-only ]] || { echo 'Usage: build.sh [--prepare-only]' >&2; exit 1; }
 prepare_only=true
fi
if ! $prepare_only; then
 [[ $EUID == 0 ]] || { echo 'Run with sudo on Arch Linux.' >&2; exit 1; }
 command -v mkarchiso >/dev/null
fi
[[ $(uname -m) == x86_64 ]] || { echo 'x86_64 build host required.' >&2; exit 1; }
for path in work profile out; do
 [[ ! -e $path && ! -L $path ]] || { echo "Move/remove previous $path/ before a fresh build." >&2; exit 1; }
done
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(date +%s)}
[[ $SOURCE_DATE_EPOCH =~ ^[0-9]+$ ]] && date -u --date="@$SOURCE_DATE_EPOCH" >/dev/null || { echo 'Invalid SOURCE_DATE_EPOCH.' >&2; exit 1; }
releng=${RAVNUX_RELENG_DIR:-/usr/share/archiso/configs/releng}
for path in profiledef.sh airootfs/etc/mkinitcpio.conf.d/archiso.conf syslinux efiboot; do
 [[ -e $releng/$path ]] || { echo "Missing Archiso template: $path" >&2; exit 1; }
done
python3 scripts/check.py
# Retain upstream boot templates and initramfs configuration, not its rescue software/services.
mkdir profile
tar -C "$releng" --exclude=./airootfs -cf - . | tar -C profile -xf -
mkdir -p profile/airootfs/etc
cp -a "$releng/airootfs/etc/mkinitcpio.conf.d" profile/airootfs/etc/
cp -a overlay/common/. profile/airootfs/
cp overlay/common/etc/pacman.conf profile/pacman.conf
cp -a overlay/live/. profile/airootfs/
# Apply live identity at startup, while retaining it in the installed overlay.
rm -f profile/airootfs/etc/os-release
mkdir -p profile/airootfs/usr/share/ravnux/root-overlay
cp -a overlay/common/. profile/airootfs/usr/share/ravnux/root-overlay/
install -Dm644 docs/GUIDE_PL.md profile/airootfs/usr/share/ravnux/guide-pl.md
install -Dm644 packages/system.txt profile/airootfs/usr/share/ravnux/system-packages.txt
install -Dm755 scripts/install.sh profile/airootfs/usr/local/bin/ravnux-install
install -Dm755 scripts/install-wizard.sh profile/airootfs/usr/local/bin/ravnux-setup
cat packages/system.txt packages/live.txt | sort -u > profile/packages.x86_64
# ISO settings are appended to the packaged profile to follow upstream bootmode changes.
cat >> profile/profiledef.sh <<'EOF'
iso_name="ravnux"
iso_label="RAVNUX_$(date -u --date="@$SOURCE_DATE_EPOCH" +%Y%m)"
iso_version="$(date -u --date="@$SOURCE_DATE_EPOCH" +%Y.%m.%d)"
iso_publisher="RAVNUX <https://github.com/stainleSSStar/RAVNUX>"
iso_application="RAVNUX XFCE Live and Installer"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15' '-b' '1M')
# This assignment intentionally REPLACES upstream's array: RAVNUX strips the
# upstream rescue airootfs, so upstream entries like /root/.automated_script.sh
# or /usr/local/bin/livecd-sound would make mkarchiso fail on missing paths.
file_permissions=(
 ["/etc/shadow"]="0:0:400"
 ["/etc/sudoers.d"]="0:0:750"
 ["/usr/share/ravnux/root-overlay/etc/sudoers.d"]="0:0:750"
 ["/usr/local/bin/ravnux-keyring-init"]="0:0:755"
 ["/usr/local/bin/ravnux-guide"]="0:0:755"
 ["/usr/share/ravnux/root-overlay/usr/local/bin/ravnux-keyring-init"]="0:0:755"
 ["/usr/local/bin/ravnux-desktop"]="0:0:755"
 ["/usr/share/ravnux/root-overlay/usr/local/bin/ravnux-desktop"]="0:0:755"
 ["/usr/share/ravnux/root-overlay/etc/sudoers.d/20-ravnux-wheel"]="0:0:440"
 ["/usr/local/bin/ravnux-install"]="0:0:755"
 ["/usr/local/bin/ravnux-setup"]="0:0:755"
 ["/usr/local/bin/ravnux-live-setup"]="0:0:755"
 ["/etc/sudoers.d/10-ravnux-live"]="0:0:440"
 ["/etc/sudoers.d/20-ravnux-wheel"]="0:0:440"
)
EOF
# Remove upstream speech boot options: this minimal image does not include speech software.
find profile/efiboot -type f -name '*speech*' -delete
sed -i '/# Accessibility boot option/,$d' profile/syslinux/archiso_sys-linux.cfg
# Keep Arch's supported paths (install_dir=arch); brand boot menu titles only.
find profile/syslinux profile/efiboot -type f \( -name '*.cfg' -o -name '*.conf' \) -exec sed -i 's/Arch Linux/RAVNUX/g' {} +
# Preserve local output while exposing diagnostics and login on the VM serial port.
# Serial last: /dev/console is ttyS0, so initramfs/systemd messages reach the VM smoke test.
find profile/syslinux profile/efiboot -type f \( -name '*.cfg' -o -name '*.conf' \) -exec sed -i '/archisobasedir=/s/$/ console=tty0 console=ttyS0,115200/' {} +
if [[ -d profile/grub ]]; then
 find profile/grub -type f -name '*.cfg' -exec sed -i 's/Arch Linux/RAVNUX/g; /archisobasedir=/s/$/ console=tty0 console=ttyS0,115200/' {} +
fi
# Explicitly enable only the services RAVNUX uses.
units=profile/airootfs/etc/systemd/system
mkdir -p "$units/multi-user.target.wants" "$units/bluetooth.target.wants"
ln -s /etc/systemd/system/pacman-init.service "$units/multi-user.target.wants/pacman-init.service"
ln -s /usr/lib/systemd/system/systemd-timesyncd.service "$units/multi-user.target.wants/systemd-timesyncd.service"
ln -s /usr/lib/systemd/system/NetworkManager.service "$units/multi-user.target.wants/NetworkManager.service"
ln -s /usr/lib/systemd/system/bluetooth.service "$units/bluetooth.target.wants/bluetooth.service"
ln -s /usr/lib/systemd/system/lightdm.service "$units/display-manager.service"
ln -s /usr/lib/systemd/system/graphical.target "$units/default.target"
ln -s /etc/systemd/system/ravnux-live-setup.service "$units/multi-user.target.wants/ravnux-live-setup.service"
# Enable the serial getty explicitly: with console=tty0 last, getty-generator does not spawn it,
# leaving the VM smoke test without a login prompt on ttyS0. The symlink must target the template.
ln -s /usr/lib/systemd/system/serial-getty@.service "$units/multi-user.target.wants/serial-getty@ttyS0.service"
: > profile/airootfs/etc/machine-id
python3 scripts/check.py
if $prepare_only; then exit 0; fi
# Fail early on renamed/missing packages instead of silently producing an incomplete image.
mapfile -t packages < profile/packages.x86_64
# mkarchiso's pacstrap verifies package signatures against the HOST keyring
# at /etc/pacman.d/gnupg (verified: an isolated GPGDir does not flow through to
# it, and the build fails with "unknown trust" for the XLibre key). The build
# therefore necessarily initializes the host keyring and locally signs the
# XLibre key. Run the build in a disposable container (as CI does) if you do
# not want to extend this machine's pacman trust.
pacman-key --init
pacman-key --populate archlinux
bash overlay/common/usr/local/bin/ravnux-keyring-init "$PWD/overlay/common/usr/share/ravnux/keyring/xlibre-archlinux.asc"
pacman --config "$PWD/profile/pacman.conf" -Sy --noconfirm
pacman --config "$PWD/profile/pacman.conf" -Si "${packages[@]}" >/dev/null
mkdir -p out
pacman -Q > out/build-host-packages.txt
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH" > out/build-info.txt
mkarchiso -v -w "$PWD/work" -o "$PWD/out" "$PWD/profile"
cp docs/GUIDE_PL.md out/GUIDE_PL.md
cp docs/AUDIT_PL.md out/AUDIT_PL.md
cp docs/PRODUCTION_AUDIT_PL.md out/PRODUCTION_AUDIT_PL.md
cp work/x86_64/airootfs/usr/share/ravnux/system-packages.txt out/requested-system-packages.txt
cp work/iso/arch/pkglist.x86_64.txt out/live-packages.txt
if grep -Eq '^xorg-server(-| )|^xf86-input-libinput ' out/live-packages.txt; then
 echo 'Unexpected Xorg server/input package in ISO.' >&2
 exit 1
fi
grep -q '^xlibre-xserver ' out/live-packages.txt
grep -q '^xlibre-input-libinput ' out/live-packages.txt
(cd out && sha256sum ./*.iso > SHA256SUMS)
