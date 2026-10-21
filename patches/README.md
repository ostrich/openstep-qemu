# Emulator and firmware patches

The build applies all four project collections: QEMU, PC SeaBIOS, SPARC
OpenBIOS and SeaBIOS-HPPA. Revisions are pinned in
[upstream.json](../upstream.json). The tables group changes by guest platform;
they are an index for review, **not an alternate application order**.

## Intel PC: NEXTSTEP 3.3 and OPENSTEP 4.2

| Project | Patch numbers | Area |
| --- | --- | --- |
| QEMU | 0001–0005 | PCnet, SB16 reset, PIC cascade and VMware SVGA modes |
| QEMU | 0006–0014 | ESP/AMD SCSI DMA, lifecycle, registers and migration; the ESP core is also used on SPARC |
| QEMU | 0015–0016 | Virtio console disconnect and output completion |
| SeaBIOS | 0001–0003 | ESP SCSI completion and LSI 53C810 discovery |
| SeaBIOS | 0004 | Optional low-memory virtqueues for OPENSTEP virtio-blk boot |

## SPARCstation 5: NEXTSTEP 3.3 and OPENSTEP 4.2

| Project | Patch numbers | Area |
| --- | --- | --- |
| QEMU | 0023–0025 | ESP timing, TCX overlap and microSPARC-II PTE bits |
| QEMU | 0031 | Carrier detection for attached Sun input devices |
| OpenBIOS | 0001–0002 | SPARC32 romvec mapping and physical fw_cfg access |

## HP 715: NEXTSTEP 3.3

| Project | Patch numbers | Area |
| --- | --- | --- |
| QEMU | 0018–0022 | NCR710 SCRIPTS, SIGP and negotiation handshakes |
| QEMU | 0026–0030 | LASI probes, Artist accesses/status/Color Recovery and CPU recovery-counter stepping |
| SeaBIOS-HPPA | 0001–0002 | Compiler build fix and relaxed boot-sector offsets |

## Shared host display

| Project | Patch number | Area |
| --- | --- | --- |
| QEMU | 0017 | VNC alongside GTK/SDL OpenGL presentation of software framebuffers |

## Apply

From the repository root:

```sh
python3 scripts/sources.py prepare
```

This fetches the pinned emulator and firmware revisions into `.sources/`, applies the
patches and records their hashes. It verifies existing prepared checkouts and
rejects unexpected changes.

For manual application, use `git apply` in an unpatched checkout of the matching
upstream revision. Each project has one complete `series`, consecutively numbered patches and
`topics/*.series` that partition it in the same global order. Follow the
matching project's `series` in order. Firmware revisions are independent of
the gitlinks bundled in upstream QEMU. Do not apply the patches again to a
checkout already prepared by the script.

The `topics/*.series` files select subsets of the same patch files for review
and testing. Their filenames retain the numbering from the complete collection.

SeaBIOS's low-memory queue allocation is enabled at runtime with
`-fw_cfg name=etc/virtio-low-queues,string=on`. It is intended for OPENSTEP
virtio-blk boot; the default allocation is unchanged.

See [patch details](../docs/patches.md) for the individual fixes and
[build instructions](../docs/build.md) to compile the patched sources.

Every release build applies all four collections. Linux builds x86 SeaBIOS,
SPARC OpenBIOS and SeaBIOS-HPPA once; the other hosts verify and reuse those
ROMs. See [NEXTSTEP RISC](../docs/risc.md) for machine-specific behavior.
