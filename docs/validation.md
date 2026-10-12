# Validation

Builds run portable source-tooling checks, device regression tests and smoke
tests of the packaged executables. Results and logs are available in
[GitHub Actions](https://github.com/ostrich/openstep-qemu/actions).

The normal build includes only the i386 emulator and qemu-img. Optional extended
Linux tests build an additional x86_64 emulator for SCSI regression coverage;
that emulator is not distributed.

Bundle smoke tests start the emulator under TCG with the bundled firmware and
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
Windows still runs the remaining 38 AMD SCSI DMA cases.

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
