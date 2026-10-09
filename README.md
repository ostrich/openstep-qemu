# OPENSTEP QEMU

A QEMU build for running **OPENSTEP 4.2 Intel**, with device and BIOS fixes for
its original drivers and support for our VMware SVGA and virtio guest drivers.

OPENSTEP exercises hardware behavior that many newer guests avoid. Bugs in
QEMU's interrupt handling, network adapter and SCSI emulation, along with
SeaBIOS's SCSI routines, can stall boot or prevent devices from working correctly. This
build corrects those paths and adds the host support needed for higher-resolution
video and guest-agent/terminal integration.

## What changes

| Device or firmware | Changes |
| --- | --- |
| PCnet network adapter | Correct descriptor-ring lengths and startup state so the original network driver can initialize and transfer packets correctly. |
| Sound Blaster 16 | Remove a spurious completion interrupt during DSP reset. |
| 8259 interrupt controller | Withdraw stale cascade requests that can leave guest disk interrupts blocked. |
| VMware SVGA | Allow resolutions up to 3840×2160 with sufficient video RAM and check framebuffer bounds. |
| AMD Am53C974 / ESP SCSI | Fix DMA transfers, page descriptors, register accesses, error reporting and migration state. |
| Virtio console | Fix disconnect handling and return pending output descriptors, supporting the guest agent and interactive terminal services. |
| SeaBIOS | Fix ESP SCSI completion, recognize QEMU's LSI 53C810, and offer low-memory virtqueues for OPENSTEP's boot loader. |

The build includes the complete maintained patch set. Firmware queue allocation
stays unchanged unless the low-memory option is explicitly enabled.
[Patch details](docs/patches.md) and [ordered patch series](patches/README.md)
are available for rebuilding or reviewing individual changes.

## Download

Get binaries, source and checksums from
[Releases](https://github.com/ostrich/openstep-qemu/releases).
Choose the archive for your **host**, not the guest:

- Linux x86-64
- Windows x86-64
- macOS arm64 (Apple Silicon) or x86-64 (Intel)

Versioned releases are built from `v*` tags. **Latest master build** is a rolling
prerelease updated after a successful build of every platform.

Each host archive includes `qemu-system-i386`, `qemu-img`, runtime libraries,
patched SeaBIOS, VGA firmware and launch examples. Windows users do not need
MSYS2 to run the downloaded binaries. OPENSTEP installation media, guest disks
and guest drivers are supplied separately.

## Run an installed guest

Extract the host archive. From its directory, launch an existing raw disk:

Linux or macOS:

```sh
sh launch/openstep.sh /path/to/openstep.raw
```

Windows PowerShell:

```powershell
.\launch\openstep.ps1 -Disk C:\VMs\openstep.raw
```

The examples use one Pentium CPU, 64 MiB RAM, EIDE storage, PCnet networking,
Sound Blaster 16 and VMware SVGA with 32 MiB video RAM. **Install the VMWareFB
guest driver before using that graphics configuration.** For a guest using
VESA, edit the launcher to use standard VGA (`-vga std`) and remove the
`vmware-svga` device.

The launchers default to TCG. On Linux with KVM available:

```sh
OPENSTEP_ACCEL=kvm sh launch/openstep.sh /path/to/openstep.raw
```

The network configuration forwards host port 2223 to guest SSH port 22; an SSH
server must be installed in the guest. Shut down OPENSTEP cleanly before closing
QEMU.

Guest drivers, installable packages and guest-service configuration belong in
[openstep-drivers](https://github.com/ostrich/openstep-drivers).
For virtio-blk boot, follow that driver's installation instructions and add:

```text
-fw_cfg name=etc/virtio-low-queues,string=on
```

Use the bundled BIOS with this option. It keeps persistent BIOS queues away
from memory overwritten by OPENSTEP's boot loader. EIDE boot does not need it.
See the [bundle guide](docs/bundle.md) for direct QEMU invocation and firmware
selection.

## Build from source

Install the [build dependencies](docs/build.md), then run:

```sh
bash build/linux.sh
```

The scripts fetch pinned upstream revisions, apply the patches, build, run
regression tests and package the results in `dist/`. Windows builds use
`build/windows.sh` in MSYS2; macOS builds use `build/macos.sh`. Both consume the
shared firmware produced by the Linux build.

[upstream.json](upstream.json) records the QEMU and SeaBIOS versions and commits.
See [build instructions](docs/build.md) for firmware transfer, output directories
and optional extended tests, and [release behavior](docs/releases.md) for CI
and download publication.

## License

Build tooling is GPL-2.0-or-later. QEMU, SeaBIOS, firmware and runtime libraries
retain their original licenses and attribution. See [COPYING](COPYING) and the
license files included with each download.
