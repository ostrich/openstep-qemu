# OPENSTEP QEMU

QEMU and patched firmware for OPENSTEP 4.2 Intel and NEXTSTEP 3.3 SPARC/HPPA. The included launchers configure
EIDE storage, PCnet networking, Sound Blaster 16 and VMware SVGA.

## Start an installed guest

From the extracted download directory:

Linux or macOS:

```sh
sh launch/openstep.sh /path/to/openstep.raw
```

Windows PowerShell:

```powershell
.\launch\openstep.ps1 -Disk C:\VMs\openstep.raw
```

The examples expect an existing raw disk with the VMWareFB guest driver
installed. For a VESA guest, edit the launcher to use `-vga std` and remove
`-vga none` and the `vmware-svga` device.

The launchers use TCG. Linux users with KVM available can select it with:

```sh
OPENSTEP_ACCEL=kvm sh launch/openstep.sh /path/to/openstep.raw
```

Host port 2223 forwards to guest SSH port 22. Install and configure an SSH server
in the guest to use it. Shut down OPENSTEP cleanly before closing QEMU, and never
mount a disk while a VM has it open.

Guest drivers, packages and service instructions are available separately from
[openstep-drivers](https://github.com/ostrich/openstep-drivers). Installation
media and guest disks are not included in this download.

## Firmware and virtio

The launchers select the bundled firmware. When running QEMU directly, pass
absolute paths for the firmware directory and BIOS:

```text
-L /path/to/download/share/qemu -bios /path/to/download/share/qemu/bios-256k.bin
```

For virtio-blk boot, install and configure the guest driver first, then add:

```text
-fw_cfg name=etc/virtio-low-queues,string=on
```

This keeps persistent BIOS queues away from memory overwritten by OPENSTEP's
boot loader. EIDE boot does not need this option. Guest-agent and terminal
services require the virtio serial ports described in their package README.

## Host requirements

- Linux uses host glibc and host audio/display services.
- macOS binaries are ad-hoc signed. The download is not notarized.
- Windows includes native runtime DLLs; MSYS2 is needed only to build it.
- Patched PC SeaBIOS, SPARC OpenBIOS and SeaBIOS-HPPA are included.
  The VGA firmware covers the PC devices used by the examples.
  Network boot ROMs are omitted, and the launchers disable NIC ROM loading.

Use `bin/qemu-system-i386` to run the guest and `bin/qemu-img` for disk-image
operations. `BUILD.json` identifies the upstream revisions, patches, firmware
and build options. Include it and your QEMU command when reporting a problem.

## NEXTSTEP RISC guests

Use `sh launch/nextstep-sparc.sh DISK.raw` for SPARCstation 5, or
`sh launch/nextstep-hppa.sh DISK.raw` for HP 715. Windows has corresponding
PowerShell launchers: `.\launch\nextstep-hppa.ps1 -Disk C:\VMs\nextstep.raw`.
These launchers use one CPU, 64 MiB RAM, TCG and no network adapter. SPARC uses
SCSI target 0; HPPA uses target 6. To attach installation media, append a
read-only SCSI CD drive at target 2. Media and disks are supplied separately.

HPPA's original graphics driver supports BW:8 grayscale and RGB:888/32 Artist
Color Recovery. Ordinary RGB:256/8 is not supported by that guest driver.
Disable HPAdvancedAudio in the guest; this build does not provide that audio
hardware. HPPA external networking remains unqualified.

Shut down through the guest first. HPPA may keep QEMU running in its final
kernel halt loop. Its last console message alone does not prove completion.
The RISC launchers provide a monitor in the terminal: use `info registers`
with your kernel's verified halt-loop address, then `quit` after shutdown.
Do not close a running guest simply because its display stopped changing.
