#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
[[ $EUID == 0 ]] || { echo 'Run with sudo on Arch Linux.' >&2; exit 1; }
command -v mkarchiso >/dev/null
[[ $(uname -m) == x86_64 ]] || { echo 'x86_64 build host required.' >&2; exit 1; }
[[ ! -e work && ! -e profile ]] || { echo 'Move/remove previous work/ and profile/ before a fresh build.' >&2; exit 1; }
# Retain upstream boot templates and initramfs configuration, not its rescue software/services.
cp -a /usr/share/archiso/configs/releng profile
cp -a profile/airootfs/etc/mkinitcpio.conf.d /tmp/ravnux-mkinitcpio-$$
rm -rf profile/airootfs
mkdir -p profile/airootfs/etc
mv /tmp/ravnux-mkinitcpio-$$ profile/airootfs/etc/mkinitcpio.conf.d
cp -a overlay/common/. profile/airootfs/
cp -a overlay/live/. profile/airootfs/
# filesystem owns /etc/os-release: apply live branding at startup instead.
rm -f profile/airootfs/etc/os-release
mkdir -p profile/airootfs/usr/share/ravnux/root-overlay
cp -a overlay/common/. profile/airootfs/usr/share/ravnux/root-overlay/
install -Dm644 packages/system.txt profile/airootfs/usr/share/ravnux/system-packages.txt
install -Dm755 scripts/install.sh profile/airootfs/usr/local/bin/ravnux-install
cat packages/system.txt packages/live.txt | sort -u > profile/packages.x86_64
# ISO settings are appended to the packaged profile to follow upstream bootmode changes.
cat >> profile/profiledef.sh <<'EOF'
iso_name="ravnux"
iso_label="RAVNUX_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="RAVNUX <https://github.com/stainleSSStar/RAVNUX>"
iso_application="RAVNUX XFCE Live and Installer"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15' '-b' '1M')
file_permissions=(
 ["/usr/local/bin/ravnux-desktop"]="0:0:755"
 ["/usr/share/ravnux/root-overlay/usr/local/bin/ravnux-desktop"]="0:0:755"
 ["/usr/share/ravnux/root-overlay/etc/sudoers.d/20-ravnux-wheel"]="0:0:440"
 ["/usr/local/bin/ravnux-install"]="0:0:755"
 ["/usr/local/bin/ravnux-live-setup"]="0:0:755"
 ["/etc/sudoers.d/10-ravnux-live"]="0:0:440"
 ["/etc/sudoers.d/20-ravnux-wheel"]="0:0:440"
)
EOF
# Keep Arch's supported paths (install_dir=arch); brand boot menu titles only.
find profile/syslinux profile/efiboot -type f \( -name '*.cfg' -o -name '*.conf' \) -exec sed -i 's/Arch Linux/RAVNUX/g' {} +
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
: > profile/airootfs/etc/machine-id
python3 scripts/check.py
# Fail early on renamed/missing packages instead of silently producing an incomplete image.
mapfile -t packages < profile/packages.x86_64
pacman -Si "${packages[@]}" >/dev/null
mkdir -p out
pacman -Q > out/build-host-packages.txt
mkarchiso -v -w "$PWD/work" -o "$PWD/out" "$PWD/profile"
cp work/x86_64/airootfs/usr/share/ravnux/system-packages.txt out/requested-system-packages.txt
cp work/iso/arch/pkglist.x86_64.txt out/live-packages.txt
(cd out && sha256sum ./*.iso > SHA256SUMS)
