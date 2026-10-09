# Example for an existing raw disk with VMWareFB installed in the guest.
param([Parameter(Mandatory=$true)][string]$Disk, [string[]]$ExtraArguments)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$DiskPath = (Resolve-Path -LiteralPath $Disk).Path
$Options = @(
    '-L', "$Root\share\qemu", '-bios', "$Root\share\qemu\bios-256k.bin",
    '-machine', 'pc,acpi=off,hpet=off,usb=off,vmport=on',
    '-accel', 'tcg', '-cpu', 'pentium', '-smp', '1', '-m', '64',
    '-drive', "file=$DiskPath,format=raw,if=ide,index=0", '-boot', 'order=c',
    '-vga', 'none', '-device', 'vmware-svga,vgamem_mb=32',
    '-netdev', 'user,id=net0,hostfwd=tcp:127.0.0.1:2223-:22',
    '-device', 'pcnet,netdev=net0,romfile=',
    '-audiodev', 'sdl,id=audio0', '-device', 'sb16,audiodev=audio0'
)
& "$Root\bin\qemu-system-i386.exe" @Options @ExtraArguments
exit $LASTEXITCODE
