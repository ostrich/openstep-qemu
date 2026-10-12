# Patch behavior and validation boundaries

PCnet fixes translate negative descriptor counts and enforce stopped/startup
state. SB16 reset no longer raises a synthetic completion interrupt. PIC cascade
withdraws an unacknowledged slave request. VMware SVGA accepts 3840x2160 with
sufficient VRAM while validating mode bounds and retaining default VRAM size.
The display console allows CPU listeners such as VNC alongside GTK/SDL OpenGL
presentation of software framebuffers. Context compatibility remains required
for guest GL rendering and GL listeners; DMABUF requirements are unchanged.

ESP/AMD SCSI changes implement actual-byte DMA accounting, MDL page descriptors,
errors/lifecycle, migration progress validation, byte lanes, illegal commands,
IOE and interrupt acknowledgement. The added regression suite preserves existing
crash tests. Synchronous negotiation, physical FIFO timing, full command stacking
and host SCSI passthrough are outside the established coverage.

Virtio console fixes avoid rethrottling after synchronous backend disconnect and
return pending output descriptors on port close. The driver/guest services rely
on these behaviors; they do not provide per-port hardware resets.

SeaBIOS waits for ESP status phase, acknowledges completion interrupts, discovers
QEMU's 53C810 PCI ID and offers opt-in low-memory virtqueues. The latter avoids
OPENSTEP boot-loader RAM probing over persistent high-memory queues; it does not
modify the guest booter. Enable via `etc/virtio-low-queues` only when needed.

Existing topic development included device qtests, Linux/Windows/OPENSTEP guest
checks and KVM/TCG runs. Those results are context, not proof that the complete
combined set has passed every host/guest release gate. No physical SB16 oracle
was available; PIC electrical/INTA equivalence remains limited. Both complete
series and individual topics apply to the pinned bases.

The AMD test registration is placed after `qtests_filter` so it composes with
PIC/SB16 registrations. No emulator change was introduced by that adjustment.
The public regression runner records actual TAP results, rather than treating
successful compilation as hardware/guest compatibility evidence.
