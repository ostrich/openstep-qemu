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

## Platform-specific coverage

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
coverage. They do not establish complete OPENSTEP guest compatibility on every
host or cover every GUI, audio and guest-service configuration.

Display-console checks on Linux cover exact VNC pixels, resizing and reconnects
at 320x240, 800x600 and 1600x1200 with GTK/Wayland, SDL and GTK/Xvfb software
OpenGL. An isolated OPENSTEP boot also matched VNC and QMP pixels at 1600x1200.
Guest GL rendering retains its VNC restriction. These GUI checks are manual,
using `tests/vnc-gl-framebuffer.py`; they are not part of headless CI and have
not been run on Windows or macOS.

## Full patchset local qualification

The complete 30-patch QEMU series replays from the pinned upstream commit to
the exact source used by the combined Linux build. All firmware collections
also replay cleanly and build from their pinned sources. The resulting Linux
bundle passes its three shipped-entry-point firmware/QMP smoke tests. RISC
qtests pass 51 cases: 13 ESP, four TCX, 19 NCR710, one LASI and 14 Artist. The
SPARC PTE matrix passes 18 expected outcomes; HP 715 recovery checks pass eight.
The x86 runner passes 111 checks. Firmware source probes pass 11 OpenBIOS
mapping cases and the HPPA strict and relaxed boot-offset matrices. Both RISC
firmware recipes also build in a clean Ubuntu 24.04 container with the CI
dependencies. HPPA firmware debug stripping preserves every ELF load segment.
Compiler prefix mapping removes private checkout paths from the packaged
executables, including runtime source-location strings.

The expanded macOS and Windows workflow configuration is linted and its release
validation is tested with offline fixtures. These local checks do not claim
that the new three-target jobs have already run on GitHub. CI retains the
actual per-host regression records with each build.
