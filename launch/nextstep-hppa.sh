#!/bin/sh
# Boot an existing NEXTSTEP 3.3 raw disk. Extra QEMU arguments follow the disk.
set -eu
if [ "$#" -lt 1 ]; then echo 'Usage: nextstep-hppa.sh DISK.raw [extra QEMU options]' >&2; exit 2; fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
disk=$1
shift
[ -f "$disk" ] || { echo 'Disk does not exist' >&2; exit 1; }
exec "$root/bin/qemu-system-hppa" -L "$root/share/qemu" -bios "$root/share/qemu/hppa-firmware.img" \
 -machine 715 -accel tcg -m 64 -smp 1 -boot order=c \
 -drive "file=$disk,format=raw,cache=writethrough,if=scsi,bus=0,unit=6" \
 -nic none -serial none -monitor stdio "$@"
