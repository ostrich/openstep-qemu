# NEXTSTEP and OPENSTEP on SPARC and HPPA

The source patchset supports NEXTSTEP 3.3 and OPENSTEP 4.2 on QEMU's
SPARCstation 5, and NEXTSTEP 3.3 on HP 715. All three have been installed
from original media and booted from their hard disks to Workspace. Every host download includes both emulators, matching
patched firmware and launchers. Start an installed disk with
`sh launch/nextstep-hppa.sh DISK.raw` or `sh launch/nextstep-sparc.sh DISK.raw`.
Windows has matching PowerShell scripts.

## SPARCstation 5

Use `launch/nextstep-sparc.sh` on Linux/macOS or
`launch/nextstep-sparc.ps1` on Windows. The launcher selects `SS-5`, one CPU,
64 MiB RAM, TCG, the bundled OpenBIOS and SCSI disk target 0. Networking is
disabled. Attach the original installation CD read-only at SCSI target 2 when
installing; remove it to test hard-disk boot.

### Emulation and firmware fixes

SPARC uses finite aggregate ESP DATA DMA timing, overlapping TCX blits and the
microSPARC-II physical PTE width. The ESP model defaults to no timing delay;
Sun4m configures 200 ns per byte, an aggregate 5 MB/s. Its timer is cancelled
on reset, cancellation and command replacement, and carries its deadline and
rate through migration. This models bus transfer time rather than individual
SCSI REQ/ACK cycles. Other ESP adapters retain their default timing.

TCX uses memmove for overlapping ordinary and raw blits. The microSPARC-II
models ignore PTE bits 31:27 as specified by the processor manual, including
MMU probes, while preserving stored reference/modified updates. Other CPU
models retain their existing PTE widths.

SPARC32 OpenBIOS treats romvec mapping addresses as hints, checks failed
reservations and preserves aligned map/unmap ranges. Its C fw_cfg driver uses
the same physical bypass ASI as its early startup code. Use both firmware
patches with the microSPARC-II correction; the original firmware's MMU mapping
of the synthetic configuration device is outside that CPU's translated range.

## HP 715

Use `launch/nextstep-hppa.sh` on Linux/macOS or
`launch/nextstep-hppa.ps1` on Windows. The launcher selects machine `715`, one
CPU, 64 MiB RAM, TCG, the bundled SeaBIOS-HPPA and SCSI disk target 6. Attach the
original installation CD read-only at target 2 when installing.

Use the original PS/2 keyboard/mouse drivers. Graphics support includes BW:8
grayscale and RGB:888/32 Artist Color Recovery. Ordinary RGB:256/8 is not
supported by the original guest driver. Disable HPAdvancedAudio because QEMU
has no matching audio implementation. Networking is disabled in the launcher
and external networking remains unqualified. Standalone guest configuration
avoids waits for unavailable configuration servers.

Read [Shutdown](#shutdown) before closing this guest: QEMU may remain running
after NEXTSTEP reaches its final kernel halt loop.

### Emulation and firmware fixes

HPPA uses the NCR710 SCRIPTS rewrite proposed by Keith Monahan, with additional
SIGP and negotiation-handshake fixes. Its authorship and original sign-off are
preserved. This is a backport of an upstream proposal, not a stable-release
backport. Negotiation remains declined. The rewrite changes migration format;
old NCR710 VM state cannot be migrated into the new controller implementation.

LASI safely handles accepted audio ID/reset probes. Artist shares its single
image-plane store between its two indexed views and implements byte-addressed
framebuffer access with bounds and mask handling. Its packed status reports
idle and available command space, consistent with the existing synchronous
FIFO model. Fractional RGB transfers and Color Recovery support the original
RGB:888/32 driver mode. Recovery filters the dithered image before independent
component lookup, and preserves the undithered backing-store path. Timed FIFO
occupancy and multiple per-window colormap selection remain unimplemented.

SeaBIOS-HPPA retains strict IODC alignment checks. Its relaxed mode additionally
accepts native-sector offsets used by the original NEXTSTEP hard-disk loader.
Transfer lengths retain the existing 2 KiB requirement. This is an intentional
compatibility extension to the strict firmware contract.

HPPA CPU recovery counting implements CR0 decrement, PSW R traps, nullified
instructions, fault rollback and trap-before-fetch ordering. The existing CPU
migration fields carry its state. NEXTSTEP uses this facility for debugger
single-stepping; storing the registers without generating traps was insufficient.
Native and remote debugger checks cover conditional branches, delay slots,
calls/returns and thread stepping. The change models architectural CPU behavior
rather than recognizing a guest debugger or patching original binaries.

## OPENSTEP 4.2 on SPARC

Use the same SS-5, 64 MiB and SCSI target settings as NEXTSTEP 3.3, with
`-icount shift=0,sleep=off` added for both installation and normal use:

```sh
sh launch/nextstep-sparc.sh DISK.raw -icount shift=0,sleep=off
```

On Windows, append the same two arguments to `nextstep-sparc.ps1`. The
multiarchitecture OPENSTEP 4.2 User CD contains SPARC boot files and a SPARC
kernel even when an archive's filename mentions only Intel. Attach it read-only
at SCSI target 2 for installation. Remove the medium for hard-disk boot.

Ordinary host-clock TCG can deliver a SCSI completion while the original guest
holds an internal sleep guard. Its callback tries to acquire the same guard,
leaving the kernel spinning. Instruction-based virtual timing completed the
base and graphical Essentials installation, repeated short SCSI commands and
native file copy/compare checks. Arbitrary extra DMA delays were insufficient
and are not included in the patchset. The original kernel and SCSA driver
remain unchanged. This timing requirement is specific to the tested 4.2 setup;
NEXTSTEP 3.3 remains qualified with ordinary TCG.

A separate early console-open wait requires carrier detect on the permanently
attached Sun mouse channel. The ESCC patch reports carrier for keyboard and
mouse after reset, while leaving RS232 channels unchanged. Reset and migration
qtests cover this behavior. It fixes the quiet cold-boot hang before Workspace.

The bundle includes `QEMU,tcx.bin` as well as patched OpenBIOS. Without the TCX
FCode, firmware falls back to serial and the framebuffer is blank. Packaging
and bundle smoke checks require that file. An unconfigured standalone guest
can also wait for a network configuration server; that is separate from either
emulation failure. Continue offline with Control-C or configure standalone
networking in the guest.

## Build

`bash build/linux.sh` builds all three guest targets and patched firmware, runs
regressions and assembles a single host bundle. macOS and Windows reuse the
verified Linux-built ROMs. See [build dependencies](build.md). The commands below
are alternatives for building RISC components individually.

Use the QEMU revision in [upstream.json](../upstream.json). From this repository:

```sh
python3 scripts/sources.py prepare --project qemu
mkdir -p out/risc/qemu
cd out/risc/qemu
../../../.sources/qemu/configure \
  --target-list=sparc-softmmu,hppa-softmmu --enable-vnc --disable-docs
ninja qemu-system-sparc qemu-system-hppa
cd ../../..
```

Build the firmware on Linux with ELF cross compilers. These are firmware tools,
not the NEXTSTEP Mach-O application compiler. Both recipes require a new output
directory, preserve the input checkout, apply the pinned patches, run focused
source tests and write firmware hashes and build records.

OpenBIOS additionally needs a native C compiler, GNU make, xsltproc and the
OpenBIOS `toke` tokenizer on PATH. The HPPA makefile also invokes `python`.

```sh
git clone https://gitlab.com/qemu-project/openbios.git OPENBIOS_SOURCE
python3 scripts/build-openbios.py \
  --source-checkout OPENBIOS_SOURCE --output out/risc/openbios \
  --cross-prefix /path/to/sparc-linux-

git clone https://github.com/hdeller/seabios-hppa.git SEABIOS_HPPA_SOURCE
python3 scripts/build-seabios-hppa.py \
  --source-checkout SEABIOS_HPPA_SOURCE --output out/risc/seabios-hppa \
  --cross-prefix /path/to/hppa-linux-
```

Select `out/risc/openbios/openbios-sparc32` with `qemu-system-sparc -machine
SS-5 -bios ...`, or `out/risc/seabios-hppa/hppa-firmware.img` with
`qemu-system-hppa -machine 715 -bios ...`. For uninstalled QEMU builds, also use
`-L .sources/qemu/pc-bios`. Keep graphics/input devices enabled with
`-display none` for headless testing; `-nographic` changes the guest console and
input hardware. Add a VNC server if an interactive display is wanted.

Use writable raw disks and the original installer with the per-machine settings
above. No original guest binaries are patched.

## Validation

The device runner covers ESP timing/lifecycle/migration, TCX, NCR710, LASI
and Artist, with TAP logs and actual pass counts. The shared x86 ESP suites
remain part of the normal x86 regression runner. Compilation is not counted as
a passing device test.
The diskless SPARC CPU matrix passed all 18 expected outcomes across both
microSPARC-II models and a SuperSPARC control, at all three PTE leaf levels.
OpenBIOS passed 11 mapping cases. The HPPA offset guard passed 24577 cases in
each strict/relaxed mode across 512-, 1024- and 2048-byte sectors.

Both installed guests booted automatically without a CD attached, launched
Workspace and the original Terminal, reported the expected architecture, and
copied and compared their kernels successfully. Each completed a native halt
and a stopped-filesystem check. These checks establish that configuration on
Linux TCG; they do not qualify RISC guest support on every release host, other
operating systems, HPPA networking/audio or migration from an older NCR710
implementation.

The Color Recovery extension passes 14 Artist qtests, including the original
six. Coverage includes fractional accesses and all 256 undithered readback
values, drawing, source-triggered overlapping blits, channel/pixel masks, independent component lookup, edge
rejection, palette changes, dirty neighbors, reset and device migration. Native
color desktop checks use the original NEXTSTEP driver. Exact hardware DAC
rounding, border padding and proprietary filter adjustments remain unverified.
Whole HPPA guest file migration showed missing input/timer progress after
restore; device-state tests do not qualify whole-system migration.

The original NEXTSTEP RGB driver was also tested on a cold-booted installed
guest. Saturated swatches and gradients rendered in color; window contents
matched pixel for pixel after covering/uncovering and moving the window. The
guest halted normally and passed an offline read-only filesystem check.

Device tests can be repeated with `tests/run-risc-qtests.py`. CPU tests require
a SPARC ELF assembler/linker:

```sh
python3 tests/risc/test-microsparc-pte.py \
  --qemu out/risc/qemu/qemu-system-sparc --data .sources/qemu/pc-bios \
  --cross-prefix /path/to/sparc-linux- --output out/risc/pte-results
```

The Linux release build also runs diskless recovery-counter checks on HP 715:
counting, nullification, trap ordering, fault rollback, branches and migration.
The separate C3700 board has a DIVA UART migration defect, so CPU-only checks
there must use `--skip-migration` and must not be called board-migration proof.

```sh
python3 tests/risc/test-hppa-recovery.py \
  --qemu out/linux-x86_64/qemu/qemu-system-hppa \
  --bios out/linux-x86_64/firmware/hppa-firmware.img \
  --data .sources/qemu/pc-bios --output out/recovery-check
```

## Shutdown

Use the guest's shutdown action before closing QEMU. HPPA normally remains in
a final kernel loop instead of exiting QEMU. With the original installed kernel,
the GUI power-off path has been observed at `halt_cpu` 0x1f5118, a self-branch
with instruction bytes `e8 1f 1f f7`; scripted shutdown has used another final
loop at 0x1f53a4. These addresses are kernel/path-specific, not universal checks.
Repeated PCs plus matching kernel instructions establish the halt. The messages
“Killing all processes” and “continuing” alone do not. The launchers provide
`-monitor stdio`; inspect `info registers`, then enter `quit` after a confirmed
halt. Do not inspect or mount a disk while QEMU still owns it.

## References

- [NCR53C710 data manual](https://www.bitsavers.org/components/ncr_symbios/scsi/53C710/NCR_53C710_53C710-1_SCSI_IO_Processor_Data_Manual_Jun92.pdf)
- [NCR710 upstream proposal](https://patchew.org/QEMU/20260701213359.1855870-1-keith@techtravels.org/)
- [microSPARC-II manual, section 5.2.3](https://temlib.org/pub/SparcStation/Hardware/Sparc32/microSPARC-II-UsersManual2.pdf)
- [HP's NGLE implementation in X11R6.3](https://www.x.org/releases/X11R6.3/tars/xc-1.tar.gz), SETUP_FB and ngleDepth8_ClearImagePlanes
- [HP LASI and IODC specifications](https://parisc.docs.kernel.org/en/latest/technical_documentation.html)
- [PA-RISC architecture references](https://parisc.docs.kernel.org/en/latest/technical_documentation.html), recovery counter and interruption ordering
- [NeXT HP graphics modes](https://www.nextop.de/NeXTAnswers/1684.html)
