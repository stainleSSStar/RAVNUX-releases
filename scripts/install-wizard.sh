#!/usr/bin/env bash
# Live-only CLI frontend. The mounted-target installer remains available separately.
set -Eeuo pipefail

fail() { echo "Error: $*" >&2; exit 1; }
validate_username() {
 local username=$1
 [[ $username =~ ^[a-z_][a-z0-9_-]{0,31}$ && $username != root && $username != ravnux ]] || fail 'Invalid username (root and ravnux are reserved).'
 if getent passwd "$username" >/dev/null; then fail 'Username already exists; choose a new account name.'; fi
}
disk_is_block() { [[ -b $1 ]]; }
partition_path() {
 if [[ $1 == *[0-9] ]]; then printf '%sp%s\n' "$1" "$2"; else printf '%s%s\n' "$1" "$2"; fi
}
validate_disk() {
 local disk=$1 listing mounts types readonly size type name holders
 disk_is_block "$disk" || fail 'Choose a block device.'
 [[ $(lsblk -dn -o TYPE "$disk") == disk ]] || fail 'Choose a whole disk, not a partition.'
 readonly=$(lsblk -dn -o RO "$disk") || fail 'Cannot inspect disk.'
 [[ $readonly == 0 ]] || fail 'Disk is read-only.'
 size=$(lsblk -bdn -o SIZE "$disk") || fail 'Cannot inspect disk size.'
 [[ $size =~ ^[0-9]+$ ]] && ((size >= 32 * 1024 * 1024 * 1024)) || fail 'Use a disk of at least 32 GiB.'
 # Includes mounted live media, mounted child partitions and active swap.
 mounts=$(lsblk -nr -o MOUNTPOINTS "$disk") || fail 'Cannot inspect mounts.'
 [[ -z ${mounts//[[:space:]]/} ]] || fail 'Disk contains mounted filesystems or active swap. It may be the live USB.'
 types=$(lsblk -nr -o TYPE "$disk") || fail 'Cannot inspect disk children.'
 while IFS= read -r type; do
  [[ $type == disk || $type == part ]] || fail 'Disk has active LVM, encryption or RAID devices.'
 done <<< "$types"
 listing=$(lsblk -nr -o KNAME "$disk") || fail 'Cannot inspect disk holders.'
 while IFS= read -r name; do
  if [[ -d /sys/class/block/$name/holders ]]; then
   holders=$(find "/sys/class/block/$name/holders" -mindepth 1 -maxdepth 1 -print -quit) || fail 'Cannot inspect disk holders.'
   [[ -z $holders ]] || fail 'Disk has active device holders.'
  fi
 done <<< "$listing"
}
confirm_erase() {
 local disk=$1 answer
 printf '\nALL DATA on %s will be erased. This is not a dual-boot installer.\n' "$disk"
 read -r -p "Type ERASE $disk to continue (anything else cancels): " answer
 [[ $answer == "ERASE $disk" ]] || fail 'Cancelled; disk was not modified.'
}
prepare_disk() {
 local disk=$1 mode=$2 target=${3:-/mnt}
 [[ $mode == uefi || $mode == bios ]] || fail 'Invalid boot mode.'
 # Recheck immediately before the first write, after the human confirmation.
 validate_disk "$disk"
 parted -s "$disk" mklabel gpt
 if [[ $mode == uefi ]]; then
  parted -s "$disk" mkpart ESP fat32 1MiB 1025MiB
  parted -s "$disk" set 1 esp on
  parted -s "$disk" mkpart primary ext4 1025MiB 100%
 else
  parted -s "$disk" mkpart BIOSBOOT 1MiB 3MiB
  parted -s "$disk" set 1 bios_grub on
  parted -s "$disk" mkpart primary ext4 3MiB 100%
 fi
 partprobe "$disk"
 udevadm settle
 local root efi
 root=$(partition_path "$disk" 2)
 efi=$(partition_path "$disk" 1)
 [[ $mode != uefi ]] || mkfs.fat -F 32 "$efi"
 mkfs.ext4 -F "$root"
 mount "$root" "$target"
 if [[ $mode == uefi ]]; then
  mkdir -p "$target/boot/efi"
  mount "$efi" "$target/boot/efi"
 fi
}
unmount_target() {
 local target=$1 attempt process reference resolved
 # GnuPG agents and package hooks may need a moment to release their handles.
 # Never hide a persistent failure with lazy or forced unmounting.
 for attempt in 1 2 3; do
  if umount -R "$target"; then return 0; fi
  [[ $attempt == 3 ]] || sleep 1
 done
 echo "Cannot unmount $target; remaining mounts and processes:" >&2
 findmnt -R "$target" >&2 || true
 for process in /proc/[0-9]*; do
  for reference in "$process/root" "$process/cwd" "$process"/fd/*; do
   resolved=$(readlink "$reference" 2>/dev/null) || continue
   case "$resolved" in
    "$target"|"$target"/*)
     printf 'PID %s holds %s\n' "${process##*/}" "$resolved" >&2
     break ;;
   esac
  done
 done
 return 1
}
main() {
 if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  echo 'Usage: sudo ravnux-setup'
  echo 'Interactive live-only installer: erase a whole disk (UEFI/BIOS, GPT/ext4).'
  echo 'Requires internet, a terminal and a disk of at least 32 GiB. No dual boot or encryption.'
  return
 fi
 (($# == 0)) || fail 'Unknown option. Use --help.'
 [[ $EUID == 0 ]] || fail 'Run sudo ravnux-setup.'
 [[ -t 0 && -t 1 ]] || fail 'Run in an interactive terminal.'
 [[ -d /run/archiso && -f /usr/share/ravnux/system-packages.txt && -d /usr/share/ravnux/root-overlay ]] ||
  fail 'Run from the RAVNUX live ISO.'
 for command in lsblk parted partprobe udevadm mkfs.fat mkfs.ext4 mount umount findmnt curl ravnux-install; do
  command -v "$command" >/dev/null || fail "Missing command: $command"
 done
 local targets
 # Never reuse or conceal mounts left by another installation attempt.
 targets=$(findmnt -rn -o TARGET) || fail 'Cannot inspect mounted filesystems.'
 if printf '%s\n' "$targets" | grep -Eq '^/mnt(/|$)'; then
  fail '/mnt or a subdirectory is already mounted. Inspect it and unmount it first.'
 fi
 [[ ! -L /mnt ]] || fail '/mnt must not be a symbolic link.'
 install -d -m 0755 /mnt
 local entries
 entries=$(find /mnt -mindepth 1 -maxdepth 1 -print -quit) || fail 'Cannot inspect /mnt.'
 [[ -z $entries ]] || fail '/mnt must be empty.'
 echo 'RAVNUX installation — dedicated disk, GPT/ext4'
 echo 'Connect to the internet first (use nmtui for Wi-Fi).'
 curl -fsSI --max-time 20 https://archlinux.org >/dev/null || fail 'Internet/HTTPS check failed. Check network and clock.'
 local mode=bios disk hostname username timezone answer identity current
 [[ ! -d /sys/firmware/efi ]] || mode=uefi
 printf '\nDetected boot mode: %s\n' "$mode"
 lsblk -d -o NAME,SIZE,MODEL,TRAN,RO
 read -r -p 'Target whole disk (e.g. /dev/nvme0n1 or /dev/sda): ' disk
 disk=$(readlink -f -- "$disk") || fail 'Cannot resolve disk.'
 validate_disk "$disk"
 # Detect replacement of removable media while prompts are being answered.
 identity=$(lsblk -bdn -o MAJ:MIN,SIZE,MODEL,SERIAL "$disk")
 read -r -p 'Computer name [ravpc]: ' hostname
 hostname=${hostname:-ravpc}
 [[ $hostname =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]] || fail 'Invalid hostname.'
 read -r -p 'Username (root and ravnux are reserved): ' username
 validate_username "$username"
 read -r -p 'Timezone [Europe/Warsaw]: ' timezone
 timezone=${timezone:-Europe/Warsaw}
 [[ $timezone != /* && $timezone != *..* && -f /usr/share/zoneinfo/$timezone ]] || fail 'Invalid timezone.'
 lsblk -o NAME,SIZE,MODEL,FSTYPE,MOUNTPOINTS "$disk"
 printf '\nPlan: %s, GPT, %s boot partition, ext4 root using remaining space.\n' "$disk" "$mode"
 printf 'Computer: %s | User: %s | Timezone: %s\n' "$hostname" "$username" "$timezone"
 confirm_erase "$disk"
 current=$(lsblk -bdn -o MAJ:MIN,SIZE,MODEL,SERIAL "$disk")
 [[ $identity == "$current" ]] || fail 'Disk identity changed. Start again.'
 trap 'echo "Installation interrupted. Partitions/files may already be written. Inspect /mnt before retrying; no automatic rollback." >&2' ERR
 prepare_disk "$disk" "$mode"
 local args=(--hostname "$hostname" --username "$username" --timezone "$timezone")
 [[ $mode != bios ]] || args+=(--bios-disk "$disk")
 # Backend retains its own INSTALL confirmation and interactive password prompt.
 ravnux-install "${args[@]}"
 unmount_target /mnt
 trap - ERR
 echo 'Installation finished. Remove the live USB when restarting.'
 read -r -p 'Restart now? [y/N]: ' answer
 [[ $answer != y && $answer != Y ]] || reboot
 return 0
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
