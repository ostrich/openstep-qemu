param(
    [Parameter(Mandatory=$true)][string]$Disk,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$QemuArgs
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$diskPath = (Resolve-Path -LiteralPath $Disk).Path
& "$root/bin/qemu-system-hppa.exe" -L "$root/share/qemu" -bios "$root/share/qemu/hppa-firmware.img" `
    -machine 715 -accel tcg -m 64 -smp 1 -boot order=c `
    -drive "file=$diskPath,format=raw,cache=writethrough,if=scsi,bus=0,unit=6" `
    -nic none -serial none -monitor stdio @QemuArgs
exit $LASTEXITCODE
