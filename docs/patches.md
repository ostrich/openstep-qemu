# What the patches change

The complete build includes fixes for three different guest platforms. Each
section below describes the affected hardware or firmware, what changes for the
guest, and the limits of that change. See the [patch index](../patches/README.md)
for filenames and application order, and [validation](validation.md) for test
coverage.

## Intel PC: NEXTSTEP 3.3 and OPENSTEP 4.2

These fixes affect PC hardware emulation used by the Intel guests. Most
individual device investigations used OPENSTEP 4.2. NEXTSTEP 3.3 application and
debugger tests do not independently qualify every patched device or the
OPENSTEP-specific guest drivers.

### Network, audio and interrupts

PCnet fixes translate negative descriptor counts and enforce stopped/startup
state so the original driver can initialize and transfer packets correctly.
SB16 reset no longer raises a synthetic completion interrupt. The 8259 PIC
withdraws stale, unacknowledged slave requests that can otherwise block disk
interrupts. No physical SB16 reference was available; PIC electrical/INTA
equivalence remains a validation limit.

### Graphics and guest integration

VMware SVGA accepts modes up to 3840×2160 with sufficient VRAM, checks framebuffer
bounds and retains the default VRAM size. The separate VMWareFB guest driver is
required to use this adapter in OPENSTEP.

Virtio console fixes avoid rethrottling after a synchronous backend disconnect
and return pending output descriptors when a port closes. The guest-agent and
interactive terminal services rely on these behaviors. The fixes do not provide
per-port hardware resets.

### SCSI and PC firmware

ESP/AMD SCSI changes implement actual-byte DMA accounting, MDL page descriptors,
error/lifecycle handling, migration progress validation, byte lanes, illegal
commands, IOE and interrupt acknowledgement. Synchronous negotiation, physical
FIFO timing, full command stacking and host SCSI passthrough are outside the
established coverage. The ESP core is also used by SPARC; its additional
machine-specific timing change is described below.

SeaBIOS waits for ESP status phase, acknowledges completion interrupts and
recognizes QEMU's LSI 53C810 PCI ID. It also offers opt-in low-memory virtqueues
for virtio-blk boot. OPENSTEP's boot loader probes RAM that can contain the
BIOS's persistent high-memory queues; the option avoids that conflict without
changing the guest booter. Enable it with
`-fw_cfg name=etc/virtio-low-queues,string=on` and the bundled PC BIOS. EIDE boot
does not need it, and default firmware allocation is unchanged.

## SPARCstation 5: NEXTSTEP 3.3 and OPENSTEP 4.2

- **ESP SCSI:** model aggregate transfer time so the original driver sees
  appropriate DMA progress. Sun4m selects 200 ns per byte; other ESP adapters
  retain their default timing. Reset, cancellation, command replacement and
  migration account for the pending transfer timer.
- **TCX graphics:** use overlap-safe copies for ordinary and raw framebuffer
  blits, avoiding corruption during overlapping moves.
- **microSPARC-II MMU:** ignore PTE bits 31:27 as specified by the processor,
  including MMU probes, while preserving reference/modified updates. Other CPU
  models retain their existing PTE widths.
- **ESCC input:** report carrier for permanently attached Sun keyboard/mouse
  channels after reset. This clears OPENSTEP 4.2's early console-open wait;
  ordinary serial channels keep their existing behavior.
- **OpenBIOS:** honor romvec mapping hints and aligned map/unmap ranges, check
  failed reservations, and access fw_cfg through the physical bypass ASI.
  These firmware changes accompany the corrected CPU PTE behavior.

See the [SPARC guide](risc.md#sparcstation-5) for configuration, hardware references
and validation details.

## HP 715: NEXTSTEP 3.3

- **NCR710 SCSI:** backport Keith Monahan's proposed SCRIPTS rewrite, with
  additional SIGP and negotiation-handshake fixes. Original authorship and
  sign-off are retained. Negotiation remains declined. The rewrite changes the
  migration format; old NCR710 VM state cannot migrate into this implementation.
- **LASI:** safely handle accepted audio ID/reset probes. This does not implement
  HPAdvancedAudio; disable that driver in the guest.
- **Artist graphics:** correct shared image-plane storage, byte accesses, masks
  and status reporting. Fractional RGB transfers and Color Recovery support the
  original RGB:888/32 driver. Timed FIFO occupancy and multiple per-window
  colormaps remain unimplemented.
- **PA-RISC CPU:** implement CR0 recovery counting and PSW R traps, including
  nullification, fault rollback and trap-before-fetch ordering. This enables
  architectural single-stepping used by NEXTSTEP debuggers without modifying
  guest binaries. Existing CPU migration fields carry the state.
- **SeaBIOS-HPPA:** retain strict IODC checks while allowing native-sector boot
  offsets in relaxed mode. This deliberately extends the strict firmware
  contract for the original hard-disk loader; transfer lengths still require
  2 KiB alignment. A separate patch fixes firmware compilation.

See the [HPPA guide](risc.md#hp-715) for graphics modes, hardware references,
shutdown and known limits. Device migration tests do not qualify whole HPPA
system migration.

## Shared host display behavior

The display-console patch allows CPU listeners such as VNC alongside GTK/SDL
OpenGL presentation of software framebuffers. It is a host display fix rather
than a new guest graphics adapter. Context compatibility remains required for
guest GL rendering and GL listeners; DMABUF requirements are unchanged.

The distributed builds do not enable GTK/OpenGL. This patch is useful when
building with those options; the bundled VNC server does not require them.
