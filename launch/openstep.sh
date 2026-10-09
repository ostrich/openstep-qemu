#!/bin/sh
# Example for an existing installed OPENSTEP raw disk, not an installer.
set -eu
if [ "$#" -lt 1 ]; then echo 'Usage: openstep.sh DISK.raw [extra QEMU options]' >&2; exit 2; fi
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
disk=$1
shift
[ -f "$disk" ] || { echo 'Disk does not exist' >&2; exit 1; }
accel=${OPENSTEP_ACCEL:-tcg}
machine=pc,acpi=off,hpet=off,usb=off,vmport=on
if [ "$accel" = kvm ]; then machine=$machine,kernel-irqchip=split; fi
case "$(uname -s)" in Darwin) audio=coreaudio ;; *) audio=sdl ;; esac
exec "$root/bin/qemu-system-i386" -L "$root/share/qemu" -bios "$root/share/qemu/bios-256k.bin" \
 -machine "$machine" -accel "$accel" -cpu pentium -smp 1 -m 64 \
 -drive "file=$disk,format=raw,if=ide,index=0" -boot order=c \
 -device vmware-svga,vgamem_mb=32 -vga none \
 -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2223-:22 -device pcnet,netdev=net0,romfile= \
 -audiodev "$audio,id=audio0" -device sb16,audiodev=audio0 \
 "$@"
