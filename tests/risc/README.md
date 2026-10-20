# RISC validation helpers

See [NEXTSTEP RISC](../../docs/risc.md) for device tests and firmware
requirements.

## Artist color desktop check

`artist-color-probe.m` is a small original-AppKit test for a disposable NEXTSTEP
3.3 HPPA desktop in RGB:888/32 mode. Build it with the native compiler and run
it from the desktop Terminal:

```sh
cc -O2 artist-color-probe.m -lNeXT -o artist-color-probe
./artist-color-probe > /tmp/artist-color-probe.log
```

Capture the six swatches and RGB ramps before the cover window appears,
after it disappears, and after the main window moves. The content must be
restored without corruption, and the moved window must contain the complete
image. The program prints lifecycle markers and exits after about 22 seconds;
those markers alone are not pixel assertions. Use screenshots to compare the
content, excluding borders affected by the recovery filter's neighborhood.
The deterministic Artist qtests separately cover storage and scanout semantics.
