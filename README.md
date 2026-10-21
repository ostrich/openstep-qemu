# OPENSTEP QEMU

Patched QEMU and firmware for running **NEXTSTEP 3.3 and OPENSTEP 4.2 on Intel PCs** and
**NEXTSTEP 3.3 / OPENSTEP 4.2 on SPARCstation 5** and
**NEXTSTEP 3.3 on HP 715**. The patches fix emulation and
firmware problems encountered by the original guest drivers. Intel guests can
also use the accelerated graphics, virtio and integration drivers available in
[openstep-drivers](https://github.com/ostrich/openstep-drivers).

## Download

Get an archive from [Releases](https://github.com/ostrich/openstep-qemu/releases)
for the computer running QEMU: Linux x86-64, Windows x86-64, macOS Apple Silicon
or macOS Intel. Each archive contains **all three guest emulators**, `qemu-img`,
runtime libraries, patched firmware and launch scripts. Windows downloads run
without MSYS2.

Versioned releases come from `v*` tags. **Latest master build** is a rolling
prerelease updated after all four host builds succeed. Installation media and
guest disks are not included.

## Choose a guest

| Guest system | Emulated machine | Program | Firmware |
| --- | --- | --- | --- |
| NEXTSTEP 3.3 / OPENSTEP 4.2 Intel | PC, Pentium | `qemu-system-i386` | SeaBIOS |
| NEXTSTEP 3.3 / OPENSTEP 4.2 SPARC | Sun SPARCstation 5 | `qemu-system-sparc` | OpenBIOS |
| NEXTSTEP 3.3 HPPA | HP 715 | `qemu-system-hppa` | SeaBIOS-HPPA |

The launch scripts below start an **already installed raw disk**, select the
matching bundled firmware and use one CPU with 64 MiB RAM. They default to TCG.
Run them from the extracted archive directory. The PC's drivers, acceleration
options and SSH forwarding do not apply to the SPARC or HPPA launchers.

### Intel PC: NEXTSTEP 3.3 and OPENSTEP 4.2

Both Intel systems have been used for application and library testing. The
launcher below is an **OPENSTEP 4.2 example**, not a NEXTSTEP 3.3 device recipe.
The additional VM drivers linked here target OPENSTEP 4.2; do not assume they
work with NEXTSTEP 3.3.

The PC patches fix PCnet startup, SB16 reset interrupts, PIC cascade handling
and AMD SCSI DMA. They also support higher-resolution VMware SVGA modes,
reliable virtio console disconnects and virtio-blk boot with patched SeaBIOS.

Linux or macOS:

```sh
sh launch/openstep.sh /path/to/openstep.raw
```

Windows PowerShell:

```powershell
.\launch\openstep.ps1 -Disk C:\VMs\openstep.raw
```

This example uses EIDE, PCnet, Sound Blaster 16 and VMware SVGA with 32 MiB video
RAM. **Install the VMWareFB guest driver before using this graphics setup.**
For a VESA guest, edit the launcher to replace `-vga none` and the
`vmware-svga` device with `-vga std`.

On Linux, select KVM with
`OPENSTEP_ACCEL=kvm sh launch/openstep.sh /path/to/openstep.raw`.
The launcher forwards host port 2223 to guest SSH port 22; install and configure
an SSH server in the guest to use it.

[Guest driver downloads](https://github.com/ostrich/openstep-drivers/releases/latest)
provide seamless mouse integration, accelerated 2D graphics, virtio storage and
networking, file transfer and terminal services. See the
[bundle guide](docs/bundle.md#intel-pc-nextstep-33-and-openstep-42) for firmware selection and
the additional option required for virtio-blk boot.

### SPARC: NEXTSTEP 3.3 and OPENSTEP 4.2

The SPARCstation 5 patches fix ESP SCSI transfer timing, overlapping TCX graphics
blits, microSPARC-II page-table handling and keyboard/mouse carrier detection. Matching OpenBIOS fixes allow the
original installer and hard-disk boot loader to work with that CPU behavior.

```sh
sh launch/nextstep-sparc.sh /path/to/nextstep.raw
```

Windows PowerShell:

```powershell
.\launch\nextstep-sparc.ps1 -Disk C:\VMs\nextstep.raw
```

The launcher uses SCSI disk target 0 and disables networking. Both systems have
been installed and tested through Workspace on Linux TCG. For OPENSTEP 4.2,
append `-icount shift=0,sleep=off` to the launch command. This avoids a SCSI
completion race in the original guest driver. See the
[SPARC guide](docs/risc.md#sparcstation-5) for configuration and patch details.

### NEXTSTEP 3.3 HPPA

The HP 715 patches fix NCR710 SCSI operation, LASI probes and Artist graphics.
They support the original driver's RGB:888/32 Color Recovery mode and PA-RISC
recovery-counter traps for debugger single-stepping. Patched SeaBIOS-HPPA also
handles the original hard-disk loader's sector offsets.

```sh
sh launch/nextstep-hppa.sh /path/to/nextstep.raw
```

Windows PowerShell:

```powershell
.\launch\nextstep-hppa.ps1 -Disk C:\VMs\nextstep.raw
```

The launcher uses SCSI disk target 6 and disables networking. Both grayscale and
Color Recovery desktops have been tested on Linux TCG. Ordinary RGB:256/8 is not
supported by the original guest driver. Disable HPAdvancedAudio in the guest;
QEMU does not implement that hardware. HPPA networking remains unqualified.

HPPA can remain in its kernel halt loop after shutdown. The launcher provides a
monitor in the terminal; confirm shutdown before entering `quit`. See the
[HPPA guide](docs/risc.md#hp-715) and [shutdown instructions](docs/risc.md#shutdown).

## Patchset and validation

Every build applies the complete maintained QEMU and firmware patchsets.
[Patch details](docs/patches.md) separate Intel PC, SPARC, HPPA and shared display
changes. The [patch index](patches/README.md) records their application order.
The fixes preserve original guest binaries; optional PC firmware queue allocation
is enabled only when requested.

Builds run device regressions and disk-free startup checks for all three
emulators. Those checks do not establish complete guest compatibility on every
host. See [validation](docs/validation.md) for tested configurations and limits.

## Build from source

Install the [build dependencies](docs/build.md), then run:

```sh
bash build/linux.sh
```

The scripts fetch pinned revisions, apply patches, build, run regression tests
and package results in `dist/`. Windows uses `build/windows.sh` in MSYS2;
macOS uses `build/macos.sh`. Both reuse firmware produced by the Linux build.

[upstream.json](upstream.json) records QEMU and all three firmware revisions.
See [build instructions](docs/build.md) and [release behavior](docs/releases.md)
for the full process.

## License

Build tooling is GPL-2.0-or-later. QEMU, firmware and runtime libraries retain
their original licenses and attribution. See [COPYING](COPYING) and the license
files included with each download.
