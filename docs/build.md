# Building host bundles

Use Bash on Linux/macOS and the MSYS2 UCRT64 Bash shell on Windows. Python 3.12 or newer,
Git, a C/C++ compiler, Ninja, pkg-config and the host libraries below are needed.
QEMU's configure step provisions its supported Python build environment.

Ubuntu example:

```sh
sudo apt-get install build-essential git python3 python3-venv ninja-build \
  pkg-config bison flex acpica-tools libglib2.0-dev libpixman-1-dev libsdl2-dev \
  libslirp-dev libfdt-dev zlib1g-dev libzstd-dev libpng-dev libjpeg-dev
bash build/linux.sh
```

macOS dependencies:

```sh
brew install glib pixman libslirp ninja pkg-config python
OPENSTEP_FIRMWARE_DIR=/absolute/verified-firmware bash build/macos.sh
```

If libslirp is absent, QEMU may fetch its pinned Meson fallback. The resulting
subproject must be included in the source archive. Runtime libraries are copied
and Mach-O dependency paths rewritten for the bundle; binaries are ad-hoc signed.
Intel and Apple Silicon build separately. Signing/notarization for publication
is future work.

Windows MSYS2 UCRT64 packages:

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

The Linux build produces `out/linux-x86_64/firmware/` containing the ROM and
BUILD.json. Transfer both unchanged to other builders. Source/config/patch/ROM
hashes are checked before use. The firmware is built once, not independently
recompiled with an unrelated host toolchain.

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

Normal builds configure only `i386-softmmu`; downloads contain
`qemu-system-i386` and `qemu-img`. For additional regression coverage:

```sh
OPENSTEP_EXTENDED_TESTS=1 OPENSTEP_BUILD_DIR=out/extended-linux bash build/linux.sh
```

The x86_64 emulator is used for tests and excluded from downloads. Changing
configure options in an existing build is rejected. Set OPENSTEP_BUILD_DIR to a
new directory under `out/` to preserve old outputs. OPENSTEP_VERSION overrides
local artifact naming; CI supplies one validated identity to firmware, binaries
and source archives. Version-tag builds use the tag version; master builds use
commit/run/attempt names, so successive uploads cannot mix identical filenames.
