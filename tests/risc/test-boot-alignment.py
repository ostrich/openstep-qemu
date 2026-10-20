#!/usr/bin/env python3
"""Compile the actual IODC medium-offset guard in strict and relaxed modes."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--cc', default='cc')
a = p.parse_args()
s = (a.source / 'src/parisc/parisc.c').read_text()
start = s.index('                    /*\n                     * Strict IODC requires')
end = s.index('#if PDC_VERY_STRICT', start)
guard = s[start:end]
prelude = '''#include <assert.h>
#include <stdio.h>
#define FW_BLOCKSIZE 2048
#define PDC_INVALID_ARG (-10)
struct drive { unsigned long blksize; };
struct disk_op { struct drive *drive_fl; };
static int check(unsigned long ARG5, unsigned long sector) {
    struct drive drive = { sector };
    struct disk_op disk_op = { &drive };
    (void)disk_op;
'''
tests = '''
    return 0;
}
int main(void) {
    unsigned long sector, offset;
    unsigned int cases = 0;
    for (sector = 512; sector <= 2048; sector *= 2) {
        for (offset = 0; offset < 8192; offset++) {
            unsigned long quantum = PDC_VERY_STRICT ? 2048 : sector;
            int expected = offset % quantum ? -10 : 0;
            assert(check(offset, sector) == expected);
            cases++;
        }
    }
    assert(check(1013374UL * 512, 512) == (PDC_VERY_STRICT ? -10 : 0));
    printf("%u offset cases passed, strict=%d\\n", cases + 1, PDC_VERY_STRICT);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='iodc-alignment-') as temp:
    source = Path(temp) / 'test.c'
    source.write_text(prelude + guard + tests)
    for strict in (0, 1):
        binary = Path(temp) / ('test-' + str(strict))
        subprocess.run([a.cc, '-O2', '-Wall', '-Wextra', '-Werror',
                        '-DPDC_VERY_STRICT=' + str(strict), str(source),
                        '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
