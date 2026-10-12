#!/usr/bin/env bash
set -euo pipefail
usage() {
 cat <<'HELP'
Usage: sudo ravnux-install --hostname NAME --username NAME [--timezone Europe/Warsaw]
                           [--target /mnt] [--bios-disk /dev/sdX]
Mount an EMPTY ext4/btrfs root at /mnt and a dedicated EMPTY FAT32 ESP at /mnt/boot/efi.
Default: UEFI. BIOS: supply the whole boot disk; GPT requires a BIOS boot partition.
Requires internet. Does not partition or format disks. Password is requested interactively.
Run sudo ravnux-install with no arguments (or sudo ravnux-setup) for the disk setup wizard.
HELP
}
fail() { echo "Error: $*" >&2; exit 1; }
validate_target_files() {
 local target=$1 bios_disk=$2 entries
 # Reject redirected boot paths and existing files before any installation writes.
 [[ ! -L $target/boot && ! -L $target/boot/efi ]] || fail 'Boot paths must not be symbolic links.'
 entries=$(find "$target" -mindepth 1 -maxdepth 1 ! -name lost+found ! -name boot -print -quit) || fail 'Cannot inspect target root.'
 [[ -z $entries ]] || fail 'Target root is not empty.'
 if [[ -e $target/boot ]]; then
  [[ -d $target/boot ]] || fail 'Target boot path must be a directory.'
  entries=$(find "$target/boot" -mindepth 1 -maxdepth 1 ! -name efi ! -name lost+found -print -quit) || fail 'Cannot inspect target boot directory.'
  [[ -z $entries ]] || fail 'Target boot directory is not empty.'
 fi
 if [[ -z $bios_disk ]]; then
  entries=$(find "$target/boot/efi" -mindepth 1 -maxdepth 1 -print -quit) || fail 'Cannot inspect ESP.'
  [[ -z $entries ]] || fail 'ESP is not empty; use a dedicated empty EFI partition.'
 fi
}
target=/mnt hostname='' username='' timezone=Europe/Warsaw bios_disk=''
if (($# == 0)); then exec /usr/local/bin/ravnux-setup; fi
while (($#)); do
 case "$1" in
  -h|--help) usage; exit 0 ;;
  --target|--hostname|--username|--timezone|--bios-disk)
   (($# >= 2)) || fail "Missing value for $1"
   case "$1" in
    --target) target=$2 ;; --hostname) hostname=$2 ;; --username) username=$2 ;;
    --timezone) timezone=$2 ;; --bios-disk) bios_disk=$2 ;;
   esac
   shift 2 ;;
  *) fail "Unknown option: $1" ;;
 esac
done
[[ $EUID == 0 ]] || fail 'Run as root.'
[[ $hostname =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]] || fail 'Invalid hostname.'
[[ $username =~ ^[a-z_][a-z0-9_-]{0,31}$ && $username != root && $username != ravnux ]] || fail 'Invalid username (root and ravnux are reserved).'
[[ $timezone != /* && $timezone != *..* && -f /usr/share/zoneinfo/$timezone ]] || fail 'Invalid timezone.'
[[ $target == /* && $target != / ]] || fail 'Target must be an absolute mount path other than /.'
target=$(realpath -e "$target")
[[ $target != / && $target != /run/archiso* && $target != /boot* && $target != /home* ]] || fail 'Unsafe target path.'
mountpoint -q "$target" || fail 'Target is not a mount point.'
root_type=$(findmnt -n -M "$target" -o FSTYPE)
[[ $root_type == ext4 || $root_type == btrfs ]] || fail 'Only unencrypted ext4/btrfs root is supported by this installer.'
root_device=$(findmnt -n -M "$target" -o SOURCE)
root_device=${root_device%%\[*}
[[ -b $root_device ]] || fail 'Target root must be a block device.'
# Encryption/LVM need explicit initramfs and boot arguments, outside this initial installer.
[[ $(lsblk -dn -o TYPE "$root_device") == part ]] || fail 'Root must be a plain partition; LUKS/LVM are not supported yet.'
validate_target_files "$target" "$bios_disk"
if [[ -z $bios_disk ]]; then
 mountpoint -q "$target/boot/efi" || fail 'Mount the ESP at target/boot/efi.'
 [[ $(findmnt -n -M "$target/boot/efi" -o FSTYPE) == vfat ]] || fail 'ESP must be FAT32.'
 [[ -d /sys/firmware/efi ]] || fail 'Boot the ISO in UEFI mode or specify --bios-disk.'
else
 [[ -b $bios_disk && $(lsblk -dn -o TYPE "$bios_disk") == disk ]] || fail 'BIOS boot device must be a whole disk.'
 root_parent=$(lsblk -dn -o PKNAME "$root_device")
 [[ $(readlink -f "$bios_disk") == /dev/$root_parent ]] || fail 'BIOS boot disk must contain the target root partition.'
fi
packages_file=/usr/share/ravnux/system-packages.txt
overlay=/usr/share/ravnux/root-overlay
[[ -f $packages_file && -d $overlay ]] || fail 'Run this installer from the RAVNUX live ISO.'
[[ -t 0 ]] || fail 'Interactive terminal required.'
printf '\nInstall RAVNUX on %s (%s), hostname %s, user %s.\n' "$root_device" "$target" "$hostname" "$username"
echo 'This installs files and a bootloader on the mounted target. Type INSTALL to continue:'
read -r confirmation
[[ $confirmation == INSTALL ]] || fail 'Cancelled.'
mapfile -t packages < "$packages_file"
packages+=(grub)
[[ -n $bios_disk ]] || packages+=(efibootmgr)
[[ $root_type != btrfs ]] || packages+=(btrfs-progs)
systemctl start pacman-init.service
# pacstrap -K creates a separate target keyring. Seed it before resolving
# signed XLibre packages; the host's private key must not be copied to disk.
install -d -m 0755 "$target/etc/pacman.d"
target_keyring=$target/etc/pacman.d/gnupg
pacman-key --gpgdir "$target_keyring" --init
pacman-key --gpgdir "$target_keyring" --populate archlinux
ravnux-keyring-init /usr/share/ravnux/keyring/xlibre-archlinux.asc "$target_keyring"
pacstrap -C /etc/pacman.conf -K "$target" "${packages[@]}"
cp -a --remove-destination "$overlay/." "$target/"
chmod 0440 "$target/etc/sudoers.d/20-ravnux-wheel"
genfstab -U "$target" > "$target/etc/fstab"
arch-chroot "$target" /bin/bash -s -- "$hostname" "$username" "$timezone" <<'CHROOT'
set -euo pipefail
printf '%s\n' "$1" > /etc/hostname
printf '127.0.0.1 localhost\n::1 localhost\n127.0.1.1 %s.localdomain %s\n' "$1" "$1" > /etc/hosts
ln -sf "/usr/share/zoneinfo/$3" /etc/localtime
hwclock --systohc
sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/;s/^#pl_PL.UTF-8 UTF-8/pl_PL.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
printf 'LANG=en_US.UTF-8\n' > /etc/locale.conf
useradd -m -G wheel -s /usr/bin/fish "$2"
passwd -l root
pacman-key --init
pacman-key --populate archlinux
ravnux-keyring-init
pacman -Q xlibre-xserver xlibre-input-libinput
# pacman -Q also resolves provisions, and xlibre-xserver provides xorg-server;
# compare installed package names instead of querying the virtual package.
installed="$(pacman -Qq)"
if printf '%s\n' "$installed" | grep -Fx xorg-server >/dev/null; then
 echo "Unexpected Xorg server in target." >&2
 exit 1
fi
visudo -cf /etc/sudoers
systemctl enable NetworkManager.service bluetooth.service lightdm.service systemd-timesyncd.service
systemctl set-default graphical.target
mkinitcpio -P
CHROOT
arch-chroot "$target" passwd "$username"
if [[ -z $bios_disk ]]; then
 # Portable UEFI fallback: works without writable firmware NVRAM (including many VMs).
 arch-chroot "$target" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=RAVNUX --removable --no-nvram
else
 arch-chroot "$target" grub-install --target=i386-pc "$bios_disk"
fi
printf '\nGRUB_DISTRIBUTOR="RAVNUX"\n' >> "$target/etc/default/grub"
arch-chroot "$target" grub-mkconfig -o /boot/grub/grub.cfg
# gnupg daemons for the seeded target keyring keep files open below $target,
# which would make it busy for a following umount; stop them before finishing.
gpgconf --homedir "$target_keyring" --kill all || true
printf '\nInstallation complete. Unmount %s, reboot and remove the ISO.\n' "$target"
