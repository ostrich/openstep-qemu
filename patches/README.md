# QEMU and SeaBIOS patches

These patches correct device emulation and BIOS behavior used by OPENSTEP 4.2
and its guest drivers. The build scripts apply the complete collections to the
upstream commits pinned in [upstream.json](../upstream.json).

| Project | Patches | Changes |
| --- | --- | --- |
| QEMU | 0001–0005 | PCnet networking, SB16 reset interrupts, PIC cascade handling and VMware SVGA 4K modes |
| QEMU | 0006–0014 | ESP/AMD SCSI DMA, migration, register handling and regression tests |
| QEMU | 0015–0016 | Virtio console disconnect handling and output completion |
| SeaBIOS | 0001–0003 | ESP SCSI completion and LSI 53C810 discovery |
| SeaBIOS | 0004 | Optional low-memory virtqueues for older boot loaders |

## Apply

From the repository root:

```sh
python3 scripts/sources.py prepare
```

This fetches both pinned upstream revisions into `.sources/`, applies the
patches and records their hashes. It verifies existing prepared checkouts and
rejects unexpected changes.

For manual application, use `git apply` in an unpatched checkout of the matching
upstream revision. Follow [qemu/series](qemu/series) or
[seabios/series](seabios/series) in order. Do not apply the patches again to a
checkout already prepared by the script.

The `topics/*.series` files select subsets of the same patch files for review
and testing. Their filenames retain the numbering from the complete collection.

SeaBIOS's low-memory queue allocation is enabled at runtime with
`-fw_cfg name=etc/virtio-low-queues,string=on`. It is intended for OPENSTEP
virtio-blk boot; the default allocation is unchanged.

See [patch details](../docs/patches.md) for the individual fixes and
[build instructions](../docs/build.md) to compile the patched sources.
