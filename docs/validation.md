# Validation

Builds run portable source-tooling checks, device regression tests and smoke
tests of the packaged executables. Results and logs are available in
[GitHub Actions](https://github.com/ostrich/openstep-qemu/actions).

The normal build includes i386, SPARC and HPPA emulators and qemu-img. Optional
extended Linux tests add an x86_64 emulator for SCSI coverage; that emulator is
not distributed. Each host runs the RISC device qtests as well as the x86 tests.
Linux also runs the 18-case SPARC PTE matrix and eight HPPA recovery-counter
cases, including HP 715 CPU-state migration.

Bundle smoke tests start each shipped emulator under TCG with its bundled
firmware and
exercise QMP shutdown. macOS bundles are tested after relocation, with rewritten
library paths and verified ad-hoc signatures. Firmware inputs are checked against
the expected source, configuration and hash.

Release checks reject incomplete platform inventories, mixed commits, modified
patch inputs, mismatched firmware and changed payloads. Publication tests use a
simulated GitHub client to exercise upload failures, superseded master commits
and tag handling.

## Host-specific coverage

Windows skips nine AMD SCSI migration cases because the file migration transport
cannot set its file handle nonblocking. Those cases run on Linux and macOS.
Windows still runs the remaining 38 AMD SCSI DMA cases. The same transport
limitation excludes five ESP migration cases and one Artist migration case
from its RISC runner, retaining explicit TAP skips and 45 other device passes.
Those six migration cases run on Linux and macOS. The exclusion path can be
checked on Unix with `tests/run-risc-qtests.py --skip-file-migration`.

PCnet has four tests on Windows and seven on Unix hosts. Three receive tests use
a Unix socket helper and are excluded on Windows. Ring-length, stopped-transmitter
and transmit ring-wrap tests run on all platforms.

These checks establish build, device regression and disk-free firmware startup
coverage. They do not establish complete guest compatibility on every
host or cover every GUI, audio and guest-service configuration.

## Host display checks

Display-console checks on Linux cover exact VNC pixels, resizing and reconnects
at 320x240, 800x600 and 1600x1200 with GTK/Wayland, SDL and GTK/Xvfb software
OpenGL. An isolated OPENSTEP boot also matched VNC and QMP pixels at 1600x1200.
Guest GL rendering retains its VNC restriction. These GUI checks are manual,
using `tests/vnc-gl-framebuffer.py`; they are not part of headless CI and have
not been run on Windows or macOS.

## Complete patchset qualification on Linux

The complete 31-patch QEMU series replays from the pinned upstream commit to
the exact source used by the current SPARC/i386 validation build. The earlier
combined Linux bundle used the first 30 patches. All firmware collections
also replay cleanly and build from their pinned sources. The resulting Linux
bundle passes its three shipped-entry-point firmware/QMP smoke tests. RISC
qtests cover 55 cases: 13 ESP, four TCX, four ESCC, 19 NCR710, one LASI and
14 Artist. The new ESCC cases pass locally along with the 17 existing SPARC
cases and 58 shared x86 SCSI cases. The
SPARC PTE matrix passes 18 expected outcomes; HP 715 recovery checks pass eight.
The x86 runner passes 111 checks. Firmware source probes pass 11 OpenBIOS
mapping cases and the HPPA strict and relaxed boot-offset matrices. Both RISC
firmware recipes also build in a clean Ubuntu 24.04 container with the CI
dependencies. HPPA firmware debug stripping preserves every ELF load segment.
Compiler prefix mapping removes private checkout paths from the packaged
executables, including runtime source-location strings.

Local workflow linting and offline release fixtures check the expanded build
configuration. For the outcome of a particular macOS or Windows build, use its
GitHub Actions run and retained per-host regression records. Linux qualification
alone does not establish guest compatibility on those hosts.


## Installed guest coverage

| Guest | Established coverage | Important limits |
| --- | --- | --- |
| Intel NEXTSTEP 3.3 | CD-root application, library, compiler-runtime and native/remote debugger tests | This is a test environment, not qualification of the OPENSTEP launcher, all PC devices or the additional VM drivers on NEXTSTEP 3.3. |
| Intel OPENSTEP 4.2 | Device-specific guest checks, KVM/TCG runs and a separate VNC/OpenGL display check | Not every device, service or display combination is qualified on every host. |
| SPARC NEXTSTEP 3.3 | Original CD installation, automatic hard-disk boot, Workspace, Terminal, kernel copy/compare, native halt and stopped-filesystem check on Linux TCG | These runs do not qualify all host platforms or other SPARC machines. |
| SPARC OPENSTEP 4.2 | Original-media Essentials installation, hard-disk boot to Workspace, Terminal, 64 short SCSI queries, eight kernel copy/compare cycles, native halt and clean stopped-filesystem check | Requires instruction-based timing (`-icount shift=0,sleep=off`), attached-input carrier fix and TCX firmware. Other hosts and optional packages remain unqualified. |
| HPPA NEXTSTEP 3.3 | Original CD installation, automatic hard-disk boot, Workspace, grayscale/Color Recovery graphics, debugger stepping and clean filesystem checks on Linux TCG | HPAdvancedAudio is not implemented; external networking is unqualified. Whole-system migration has shown missing input/timer progress after restore. |

See the [RISC guide](risc.md) for the machine settings, graphics checks and
hardware references behind the SPARC and HPPA results.
