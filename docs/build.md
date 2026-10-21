# Building host bundles

Use Bash on Linux/macOS and the MSYS2 UCRT64 Bash shell on Windows. Python 3.12 or newer,
Git, a C/C++ compiler, Ninja, pkg-config and the host libraries below are needed.
QEMU's configure step provisions its supported Python build environment.

Every normal build produces `qemu-system-i386`, `qemu-system-sparc`,
`qemu-system-hppa` and `qemu-img` in one host archive. Linux also builds the
three firmware images; macOS and Windows reuse those verified images.

## Linux

Ubuntu example:

```sh
sudo apt-get install build-essential git python3 python3-venv ninja-build \
  pkg-config bison flex acpica-tools libglib2.0-dev libpixman-1-dev libsdl2-dev \
  libslirp-dev libfdt-dev zlib1g-dev libzstd-dev libpng-dev libjpeg-dev \
  gcc-hppa-linux-gnu gcc-sparc64-linux-gnu xsltproc fcode-utils python-is-python3
bash build/linux.sh
```

## macOS

Dependencies:

```sh
brew install glib pixman libslirp ninja pkg-config python
OPENSTEP_FIRMWARE_DIR=/absolute/verified-firmware bash build/macos.sh
```

If libslirp is absent, QEMU may fetch its pinned Meson fallback. The resulting
subproject must be included in the source archive. Runtime libraries are copied
and Mach-O dependency paths rewritten for the bundle; binaries are ad-hoc signed.
Intel and Apple Silicon build separately. Signing/notarization for publication
is future work.

## Windows

MSYS2 UCRT64 packages:

```sh
pacman -S --needed base-devel git bison flex \
  mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-python \
  mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkgconf \
  mingw-w64-ucrt-x86_64-glib2 mingw-w64-ucrt-x86_64-pixman \
  mingw-w64-ucrt-x86_64-SDL2 mingw-w64-ucrt-x86_64-libslirp
OPENSTEP_FIRMWARE_DIR=/absolute/verified-firmware bash build/windows.sh
```

A Windows user running the finished bundle does not need MSYS2. The build uses
native MinGW DLLs; unresolved dependencies or MSYS runtime imports are rejected.

## Shared firmware

The Linux build produces `out/linux-x86_64/firmware/` containing `bios.bin`,
`openbios-sparc32`, `hppa-firmware.img` and `BUILD.json`. Transfer the whole
directory unchanged to other builders. Source/config/patch/ROM
hashes are checked before use. The firmware is built once, not independently
recompiled with an unrelated host toolchain.

## Build inputs and output directories

BUILD_JOBS sets parallelism. PYTHON selects the build interpreter. Build scripts
require the installed tools; they do not install system packages automatically.
Run `python3 scripts/sources.py check` for input validation and
`python3 scripts/sources.py verify` to detect source drift.

If fetch/application is interrupted before its state record is written, inspect
and preserve the partial checkout. Rename it out of `.sources/` before retrying;
no destructive cleanup/reset is automatic. Changed pins/patches likewise require
a new checkout/output workspace. Existing distribution files are never replaced.

References: [QEMU build environment](https://www.qemu.org/docs/master/devel/build-environment.html)
and [MSYS2 CI](https://www.msys2.org/docs/ci/).

SeaBIOS is built from an exported patched tree with an explicit distribution
version, avoiding dirty-checkout hostname/date strings in its ROM. The output
manifests keep exact source/config/firmware and tool hashes/version information.

Normal builds configure `i386-softmmu,sparc-softmmu,hppa-softmmu`; every host
download contains those three emulators and `qemu-img`. Linux also needs the
ELF cross compilers and FCode tools listed above to build the shared firmware.
Set `OPENSTEP_SPARC_CROSS` and `OPENSTEP_HPPA_CROSS` to override their default
`sparc64-linux-gnu-` and `hppa-linux-gnu-` prefixes. For additional regression coverage:

```sh
OPENSTEP_EXTENDED_TESTS=1 OPENSTEP_BUILD_DIR=out/extended-linux bash build/linux.sh
```

The x86_64 emulator is used for tests and excluded from downloads. Changing
configure options in an existing build is rejected. Set OPENSTEP_BUILD_DIR to a
new directory under `out/` to preserve old outputs. OPENSTEP_VERSION overrides
local artifact naming; CI supplies one validated identity to firmware, binaries
and source archives. Version-tag builds use the tag version; master builds use
commit/run/attempt names, so successive uploads cannot mix identical filenames.

## CI rebuilds and caches

Documentation-only changes skip the build workflow, except `docs/bundle.md`,
which is included in the distributed bundles. Tags and manual runs always build
every host. Master code changes also build every host so release artifacts share
one commit and firmware identity.

Pull requests changing only a platform build script or launcher test the affected
hosts. Linux still runs to produce the shared firmware. Shared code,
patches, packaging, tests, or workflow changes run the full matrix.

CI caches ccache compiler results, Python downloads, and Homebrew downloads per
host OS and architecture. MSYS2 also uses its built-in dependency cache. Compiler
results are validated against compiler contents; dependencies are still installed
and configuration, regression tests, packaging, and bundle smoke tests run each
time. Build directories and release artifacts are not restored from caches.
To use compiler caching locally, install ccache and set `OPENSTEP_CCACHE=1`.

Device qtests run for all three guests on every host. Linux additionally runs
diskless HPPA recovery-counter and SPARC PTE checks. Bundle smoke tests start each shipped
emulator through its launcher with its shipped ROM and QMP. These checks do
not imply that a complete guest installation was tested on every host. See
[the RISC guide](risc.md) for architecture tests and machine-specific settings.

Builds map checkout paths out of compiler-generated source locations, including
runtime diagnostics, and remove debug sections from the distributed HPPA ROM.
The original firmware build output remains available for debugging. Packaging
rejects binaries that still contain the checkout path; public build records
use a source-root placeholder instead of a local path.
