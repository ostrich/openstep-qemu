# Using the download

Each host download contains three emulators, their patched firmware, `qemu-img`
and launch scripts. Choose the archive for your host computer, then choose the
launcher for your guest below. Installation media and guest disks are supplied
separately. The launchers expect an already installed raw disk.

| Guest | Emulator | Firmware in `share/qemu/` | Disk target |
| --- | --- | --- | --- |
| NEXTSTEP 3.3 / OPENSTEP 4.2 Intel PC | `qemu-system-i386` | `bios-256k.bin` | EIDE |
| NEXTSTEP 3.3 SPARCstation 5 | `qemu-system-sparc` | `openbios-sparc32` | SCSI 0 |
| NEXTSTEP 3.3 HP 715 | `qemu-system-hppa` | `hppa-firmware.img` | SCSI 6 |

All launchers select their bundled firmware, one CPU, 64 MiB RAM and TCG.
Run the commands from the extracted download directory. Extra QEMU arguments
can be appended to the launcher command.

## Intel PC: NEXTSTEP 3.3 and OPENSTEP 4.2

Both systems run with `qemu-system-i386`. NEXTSTEP 3.3 Intel has been used in
CD-root test environments for application, library and debugger qualification.
The example below is configured for **OPENSTEP 4.2 with additional guest
drivers**. It is not a verified NEXTSTEP 3.3 launch configuration; use devices
and drivers appropriate to that guest. In particular, the VMWareFB and virtio
packages linked below are not qualified for NEXTSTEP 3.3.

Linux or macOS:

```sh
sh launch/openstep.sh /path/to/openstep.raw
```

Windows PowerShell:

```powershell
.\launch\openstep.ps1 -Disk C:\VMs\openstep.raw
```

The PC example uses EIDE storage, PCnet networking, Sound Blaster 16 and VMware
SVGA. It expects the **VMWareFB guest driver to be installed**. For a VESA guest,
edit the launcher to replace `-vga none` and the `vmware-svga` device with
`-vga std`.

Linux users with KVM available can select it with:

```sh
OPENSTEP_ACCEL=kvm sh launch/openstep.sh /path/to/openstep.raw
```

Host port 2223 forwards to guest SSH port 22. Install and configure an SSH server
in the guest to use it. Additional guest drivers, packages and service
instructions are available from
[openstep-drivers](https://github.com/ostrich/openstep-drivers).

### PC firmware and virtio boot

When invoking the PC emulator directly, select its firmware explicitly:

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
These PC instructions do not apply to SPARC or HPPA.

## SPARCstation 5: NEXTSTEP 3.3 and OPENSTEP 4.2

Linux or macOS:

```sh
sh launch/nextstep-sparc.sh /path/to/nextstep.raw
```

Windows PowerShell:

```powershell
.\launch\nextstep-sparc.ps1 -Disk C:\VMs\nextstep.raw
```

The launcher uses machine `SS-5`, SCSI disk target 0 and no network adapter.
For OPENSTEP 4.2, append `-icount shift=0,sleep=off` to either launch command.
It avoids a completion race in the original guest SCSI driver.
For installation, attach the original CD read-only at SCSI target 2. See the
[SPARC guide](https://github.com/ostrich/openstep-qemu/blob/master/docs/risc.md#sparcstation-5)
for emulation details and tested configurations.

## HP 715: NEXTSTEP 3.3

Linux or macOS:

```sh
sh launch/nextstep-hppa.sh /path/to/nextstep.raw
```

Windows PowerShell:

```powershell
.\launch\nextstep-hppa.ps1 -Disk C:\VMs\nextstep.raw
```

The launcher uses machine `715`, SCSI disk target 6 and no network adapter.
For installation, attach the original CD read-only at target 2.

The original graphics driver supports BW:8 grayscale and RGB:888/32 Artist
Color Recovery. Ordinary RGB:256/8 is not supported by that guest driver.
Disable HPAdvancedAudio; QEMU does not implement that hardware. HPPA external
networking remains unqualified. See the
[HPPA guide](https://github.com/ostrich/openstep-qemu/blob/master/docs/risc.md#hp-715)
for details.

### HPPA shutdown

Shut down through the guest first. HPPA may keep QEMU running in its final
kernel halt loop. The last console message alone does not prove completion.
The launcher provides a monitor in the terminal: use `info registers` with your
kernel's verified halt-loop address, then `quit` after shutdown. See the
[shutdown guide](https://github.com/ostrich/openstep-qemu/blob/master/docs/risc.md#shutdown)
for observed addresses and their limits. Do not close the guest simply because
its display stopped changing.

## Host requirements and reporting problems

- Linux uses host glibc and host audio/display services.
- macOS binaries are ad-hoc signed. The download is not notarized.
- Windows includes native runtime DLLs; MSYS2 is needed only to build it.
- Network boot ROMs are omitted. PC launchers disable NIC ROM loading.

Shut down every guest cleanly before closing QEMU. Never mount or modify a disk
while a VM has it open. Use `bin/qemu-img` for image operations on stopped disks.
`BUILD.json` identifies source revisions, patches, firmware and build options.
Include it and your QEMU command when reporting a problem.

## Linux display libraries

Linux bundles include SDL and the application libraries. Wayland, GBM, DRM
and OpenGL/Vulkan libraries come from the host so they match its Mesa or
vendor drivers and compositor plugins. A normal desktop installation provides
these libraries. Do not copy another distribution's graphics stack into the
bundle: an older Wayland library can prevent a newer Mesa EGL driver loading.
