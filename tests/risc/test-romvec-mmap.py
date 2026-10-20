#!/usr/bin/env python3
"""Exercise the actual romvec mapping functions with a bounded mock allocator."""
import argparse
from pathlib import Path
import subprocess
import tempfile

PRELUDE = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
typedef uint32_t ucell;
#define PAGE_SIZE 4096
#define pointer2cell(p) ((ucell)(uintptr_t)(p))
#define cell2pointer(v) ((char *)(uintptr_t)(v))
#define DPRINTF(...) ((void)0)
static unsigned claims, maps, releases, unmaps, last_size;
static ucell last_virt;
static uint64_t last_phys;
static int occupied, exhausted, map_error;
static void reset(void) {
    claims = maps = releases = unmaps = last_size = 0;
    last_virt = 0; last_phys = 0;
    occupied = exhausted = map_error = 0;
}
static ucell ofmem_claim_virt(ucell hint, ucell size, ucell align) {
    claims++; last_size = size;
    if (exhausted) return (ucell)-1;
    if (align) { assert(align == PAGE_SIZE); return 0x80000000; }
    if (!hint || occupied) return (ucell)-1;
    return hint;
}
static int ofmem_arch_default_translation_mode(uint64_t phys) { return 0; }
static int ofmem_map(uint64_t phys, ucell virt, ucell size, int mode) {
    assert(virt != (ucell)-1);
    assert(!(virt & 4095)); assert(!(size & 4095));
    assert(size && size <= (ucell)-1 - virt);
    maps++; last_phys = phys; last_virt = virt; last_size = size;
    return map_error;
}
static void ofmem_release_virt(ucell virt, ucell size) {
    releases++; last_virt = virt; last_size = size;
}
static void ofmem_unmap(ucell virt, ucell size) {
    unmaps++; last_virt = virt; last_size = size;
}
'''
TESTS = r'''
int main(void) {
    char *p;
    reset(); p = obp_dumb_mmap(NULL, 3, 0x50800000, 0x100000);
    assert(pointer2cell(p) == 0x80000000 && claims == 1 && maps == 1);
    assert(last_phys == UINT64_C(0x350800000));
    reset(); p = obp_dumb_mmap(cell2pointer(0x90000000), 0, 0x1000, 4096);
    assert(pointer2cell(p) == 0x90000000 && claims == 1);
    reset(); occupied = 1;
    p = obp_dumb_mmap(cell2pointer(0x90000000), 0, 0x1000, 4096);
    assert(pointer2cell(p) == 0x80000000 && claims == 2 && maps == 1);
    reset(); p = obp_dumb_mmap(cell2pointer((ucell)-1), 0, 0x1000, 4096);
    assert(pointer2cell(p) == 0x80000000 && claims == 1);
    reset(); exhausted = 1; p = obp_dumb_mmap(NULL, 0, 0x1000, 4096);
    assert(!p && maps == 0);
    reset(); map_error = 1; p = obp_dumb_mmap(NULL, 0, 0x1000, 4096);
    assert(!p && releases == 1);
    reset(); p = obp_dumb_mmap(NULL, 0, 0x1000, 0);
    assert(!p && claims == 0 && maps == 0);
    reset(); p = obp_dumb_mmap(NULL, 0, 0x1000, (unsigned)-1);
    assert(!p && claims == 0 && maps == 0);
    reset(); p = obp_dumb_mmap(NULL, 0, 0x50800003, 4094);
    assert(pointer2cell(p) == 0x80000003 && last_size == 8192);
    assert(last_phys == 0x50800000);
    obp_dumb_munmap(p, 4094);
    assert(unmaps == 1 && releases == 1 && last_virt == 0x80000000);
    assert(last_size == 8192);
    reset(); p = obp_dumb_mmap(cell2pointer(0xfffff000), 0, 0x1000, 8192);
    assert(pointer2cell(p) == 0x80000000 && claims == 1);
    reset(); obp_dumb_munmap(cell2pointer(0xfffff000), 8192);
    assert(!unmaps && !releases);
    puts("11 romvec mapping cases passed");
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    source = (args.source / 'arch/sparc32/lib.c').read_text()
    start = source.find('static unsigned int obp_io_map_size(')
    if start < 0:
        start = source.index('char *obp_dumb_mmap(')
    end = source.index('\nchar *obp_memalloc(', start)
    with tempfile.TemporaryDirectory(prefix='openbios-map-') as temp:
        folder = Path(temp)
        c = folder / 'test.c'
        c.write_text(PRELUDE + source[start:end] + TESTS)
        binary = folder / 'test'
        subprocess.run([args.cc, '-O2', '-Wall', '-Wextra',
                        '-Wno-unused-parameter', str(c), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
