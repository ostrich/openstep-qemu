#!/bin/sh
# Boot an installed SPARC raw disk. OPENSTEP 4.2 needs -icount shift=0,sleep=off.
# Extra QEMU arguments follow the disk.
set -eu
if [ "$#" -lt 1 ]; then echo 'Usage: nextstep-sparc.sh DISK.raw [extra QEMU options]' >&2; exit 2; fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
disk=$1
shift
[ -f "$disk" ] || { echo 'Disk does not exist' >&2; exit 1; }
exec "$root/bin/qemu-system-sparc" -L "$root/share/qemu" -bios "$root/share/qemu/openbios-sparc32" \
 -machine SS-5 -accel tcg -m 64 -smp 1 -boot order=c \
 -drive "file=$disk,format=raw,cache=writethrough,if=scsi,bus=0,unit=0" \
 -nic none -serial none -monitor stdio "$@"
