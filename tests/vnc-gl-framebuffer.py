#!/usr/bin/env python3
"""Compare VNC pixels, resize and reconnect under local OpenGL presentation.

Requires a working GTK/SDL OpenGL display. Uses no guest disk or credentials.
The QMP/RFB clients are also reusable for contained display checks.
"""

import argparse, pathlib, subprocess, socket, time, json, struct, os, hashlib


class QMP:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        self.s.settimeout(10)
        self.s.connect(str(path))
        self.f = self.s.makefile("rwb")
        self.f.readline()
        self.call("qmp_capabilities")

    def call(self, name, args=None):
        self.f.write(
            (json.dumps({"execute": name, "arguments": args or {}}) + "\n").encode()
        )
        self.f.flush()
        while True:
            r = json.loads(self.f.readline())
            if "error" in r:
                raise RuntimeError(r)
            if "return" in r:
                return r["return"]


class RFB:
    def read(self, n):
        b = b""
        while len(b) < n:
            d = self.s.recv(n - len(b))
            assert d
            b += d
        return b

    def __init__(self, endpoint):
        if isinstance(endpoint, tuple):
            self.s = socket.create_connection(endpoint, timeout=10)
        else:
            self.s = socket.socket(socket.AF_UNIX)
            self.s.settimeout(10)
            self.s.connect(str(endpoint))
        assert self.read(12) == b"RFB 003.008\n"
        self.s.sendall(b"RFB 003.008\n")
        n = self.read(1)[0]
        security = self.read(n)
        assert 1 in security
        self.s.sendall(b"\x01")
        assert self.read(4) == b"\0" * 4
        self.s.sendall(b"\x01")
        h = self.read(24)
        self.w, self.h = struct.unpack(">HH", h[:4])
        self.read(struct.unpack(">I", h[20:])[0])
        self.s.sendall(
            b"\0" * 4
            + struct.pack(">BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        )
        self.s.sendall(struct.pack(">BBHiii", 2, 0, 3, 0, -223, -239))
        self.pixels = bytearray(self.w * self.h * 4)

    def update(self):
        self.s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, self.w, self.h))
        while True:
            kind = self.read(1)[0]
            if kind == 0:
                h = self.read(3)
                n = struct.unpack(">H", h[1:])[0]
                for _ in range(n):
                    x, y, w, h, enc = struct.unpack(">HHHHi", self.read(12))
                    if enc == -223:
                        self.w, self.h = w, h
                        self.pixels = bytearray(w * h * 4)
                    elif enc == -239:
                        self.read(w * h * 4 + ((w + 7) // 8) * h)
                    else:
                        assert enc == 0, enc
                        b = self.read(w * h * 4)
                        for row in range(h):
                            self.pixels[
                                ((y + row) * self.w + x)
                                * 4 : ((y + row) * self.w + x + w)
                                * 4
                            ] = b[row * w * 4 : (row + 1) * w * 4]
                return
            elif kind == 2:
                continue
            elif kind == 3:
                h = self.read(7)
                self.read(struct.unpack(">I", h[3:])[0])
            else:
                raise RuntimeError("Unexpected RFB message " + str(kind))

    def rgb(self):
        return bytes(
            c
            for i in range(0, len(self.pixels), 4)
            for c in (self.pixels[i + 2], self.pixels[i + 1], self.pixels[i])
        )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--qemu", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--display", default="gtk,gl=on")
    p.add_argument("--gdk")
    p.add_argument("--reject-gl", action="store_true")
    a = p.parse_args()
    out = pathlib.Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    binary_sha256 = hashlib.sha256(pathlib.Path(a.qemu).read_bytes()).hexdigest()

    log = (out / "qemu.log").open("wb")
    env = os.environ.copy()
    if a.gdk:
        env["GDK_BACKEND"] = a.gdk
    vga = [
        "-vga",
        "none",
        "-device",
        "virtio-vga-gl" if a.reject_gl else "vmware-svga,addr=04.0,vgamem_mb=32",
    ]
    cmd = [
        str(pathlib.Path(a.qemu).resolve()),
        "-L",
        str(pathlib.Path(a.data).resolve()),
        "-name",
        "vnc-gl-framebuffer-test",
        "-nodefaults",
        "-machine",
        "pc",
        "-m",
        "32",
        *vga,
        "-display",
        a.display,
        "-vnc",
        "unix:" + str(out / "vnc.sock"),
        "-qmp",
        "unix:" + str(out / "qmp.sock") + ",server=on,wait=off",
        "-qtest",
        "unix:" + str(out / "qtest.sock") + ",server=on,wait=off",
        "-qtest-log",
        "/dev/null",
        "-S",
    ]
    proc = subprocess.Popen(cmd, stdout=log, stderr=log, env=env)
    q = None
    try:
        if a.reject_gl:
            code = proc.wait(timeout=10)
            assert code != 0
            assert "incompatible with the GL context" in (out / "qemu.log").read_text()
            print("Guest GL console still rejects VNC")
            raise SystemExit(0)
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if proc.poll() is not None:
                break
            if (out / "qtest.sock").exists() and (out / "vnc.sock").exists():
                try:
                    q = QMP(out / "qmp.sock")
                    break
                except OSError:
                    pass
            time.sleep(0.05)
        assert q is not None and proc.poll() is None, (out / "qemu.log").read_text()
        t = socket.socket(socket.AF_UNIX)
        t.settimeout(10)
        t.connect(str(out / "qtest.sock"))
        f = t.makefile("rwb")

        def test(command):
            f.write((command + "\n").encode())
            f.flush()
            r = f.readline().decode().strip()
            assert r.startswith("OK"), r
            return r

        def pci(offset, value):
            test("outl 0xcf8 " + hex(0x80002000 + offset))
            test("outl 0xcfc " + hex(value))

        pci(0x10, 0x1001)
        pci(0x14, 0xE0000000)
        pci(0x18, 0xE2000000)
        pci(4, 3)

        def reg(index, value):
            test("outl 0x1000 " + str(index))
            test("outl 0x1001 " + str(value))

        for offset, value in [(0, 16), (4, 65536), (8, 16), (12, 16)]:
            test("writel " + hex(0xE2000000 + offset) + " " + str(value))
        reg(20, 1)
        results = []
        for w, h, color in [
            (320, 240, 0x123456),
            (800, 600, 0xABCDEF),
            (1600, 1200, 0x2468AC),
        ]:
            reg(2, w)
            reg(3, h)
            reg(1, 1)
            q.call("screendump", {"filename": str(out / "mode.ppm")})
            for offset, value in [
                (16, 2),
                (20, color),
                (24, 0),
                (28, 0),
                (32, w),
                (36, h),
                (8, 40),
                (12, 16),
            ]:
                test("writel " + hex(0xE2000000 + offset) + " " + str(value))
            reg(21, 1)
            q.call("screendump", {"filename": str(out / "frame.ppm")})
            ppm = (out / "frame.ppm").read_bytes()
            head, rgb = ppm.split(b"\n", 3)[:3], ppm.split(b"\n", 3)[3]
            assert head == [b"P6", f"{w} {h}".encode(), b"255"], head
            expected = bytes((color >> 16, (color >> 8) & 255, color & 255)) * (w * h)
            assert rgb == expected, (
                w,
                h,
                rgb[:16].hex(),
                test("readl 0xe0000000"),
                test("readl 0xe200000c"),
            )
            if not results:
                rfb = RFB(out / "vnc.sock")
            end = time.monotonic() + 10
            while time.monotonic() < end:
                rfb.update()
                if (rfb.w, rfb.h) == (w, h) and rfb.rgb() == rgb:
                    break
            else:
                raise AssertionError("VNC pixels or resize differ from framebuffer")
            rfb.s.close()
            rfb = RFB(out / "vnc.sock")
            rfb.update()
            assert (rfb.w, rfb.h) == (w, h) and rfb.rgb() == rgb
            results.append(
                {
                    "width": w,
                    "height": h,
                    "rgb_sha256": hashlib.sha256(rgb).hexdigest(),
                    "vnc_pixels_resize_reconnect": "passed",
                }
            )
            print(results[-1], flush=True)
        rfb.s.close()
        (out / "results.json").write_text(
            json.dumps(
                {
                    "display": a.display,
                    "gdk": a.gdk,
                    "binary_sha256": binary_sha256,
                    "frames": results,
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        if q:
            try:
                q.call("quit")
            except (OSError, ValueError):
                pass
        if proc.poll() is None:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=5)
        log.close()


if __name__ == "__main__":
    main()
