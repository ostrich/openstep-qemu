#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PLATFORM=${1:?Usage: common.sh linux|macos|windows}
PYTHON=${PYTHON:-python3}
ARCH=$(uname -m)
case "$ARCH" in aarch64) ARCH=arm64 ;; amd64) ARCH=x86_64 ;; esac
OUT=$("$PYTHON" -c 'from pathlib import Path; import sys; root=Path(sys.argv[1]).resolve(); p=Path(sys.argv[2]); p=(p if p.is_absolute() else root/p).resolve(); p.relative_to(root/"out"); print(p.as_posix())' "$ROOT" "${OPENSTEP_BUILD_DIR:-out/$PLATFORM-$ARCH}")
TARGETS=i386-softmmu
TEST_ARGS=()
if [[ "${OPENSTEP_EXTENDED_TESTS:-0}" == 1 ]]; then
    TARGETS+=,x86_64-softmmu
    TEST_ARGS+=(--extended)
fi
JOBS=${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}
mkdir -p "$OUT" "$ROOT/work/tmp"
export TMPDIR="$ROOT/work/tmp"
export PIP_CACHE_DIR="$ROOT/work/cache/pip"
export XDG_CACHE_HOME="$ROOT/work/cache"
"$PYTHON" "$ROOT/scripts/sources.py" prepare
if [[ "$PLATFORM" == linux ]]; then
    printf '%s\n' 'Building the complete SeaBIOS patch set...'
    "$PYTHON" "$ROOT/scripts/build-seabios.py" --output "$OUT/seabios" --jobs "$JOBS"
    mkdir -p "$OUT/firmware"
    cp "$OUT/seabios/bios.bin" "$OUT/firmware/bios.bin"
    "$PYTHON" "$ROOT/scripts/firmware.py" record "$OUT/firmware"
else
    : "${OPENSTEP_FIRMWARE_DIR:?Supply the verified firmware directory built by build/linux.sh}"
    "$PYTHON" "$ROOT/scripts/firmware.py" verify "$OPENSTEP_FIRMWARE_DIR"
    mkdir -p "$OUT/firmware"
    cp "$OPENSTEP_FIRMWARE_DIR/bios.bin" "$OPENSTEP_FIRMWARE_DIR/BUILD.json" "$OUT/firmware/"
fi
mkdir -p "$OUT/qemu"
cd "$OUT/qemu"
configure=(--target-list="$TARGETS" --disable-werror --disable-docs
    --disable-rust --disable-gtk --disable-opengl --enable-vnc --enable-slirp
    --disable-guest-agent --prefix=/ --python="$(command -v "$PYTHON")")
case "$PLATFORM" in
    linux) configure+=(--enable-kvm --enable-sdl --audio-drv-list=sdl) ;;
    macos) configure+=(--disable-kvm --disable-hvf --disable-sdl --enable-cocoa --audio-drv-list=coreaudio) ;;
    windows) configure+=(--disable-kvm --disable-whpx --enable-sdl --audio-drv-list=sdl) ;;
    *) echo "Unknown platform: $PLATFORM" >&2; exit 2 ;;
esac
printf '%s\n' "Configuring QEMU for $PLATFORM/$ARCH..."
if [[ ! -f build.ninja ]]; then
    "$ROOT/.sources/qemu/configure" "${configure[@]}"
    "$PYTHON" -c 'import json,sys; from pathlib import Path; Path("configure-args.json").write_text(json.dumps(sys.argv[1:],indent=2)+"\n")' "${configure[@]}"
else
    "$PYTHON" -c 'import json,sys; from pathlib import Path; expected=sys.argv[1:]; actual=json.loads(Path("configure-args.json").read_text()); assert actual==expected, "Configure options changed; preserve this build and set OPENSTEP_BUILD_DIR to a new directory"' "${configure[@]}"
fi
printf '%s\n' "Building $TARGETS, qemu-img and regression tests..."
ninja -j "$JOBS"
"$PYTHON" "$ROOT/tests/run-qtests.py" --build "$OUT/qemu" --output "$OUT/tests" "${TEST_ARGS[@]}"
"$PYTHON" "$ROOT/scripts/package.py" --platform "$PLATFORM" --output "$OUT"
