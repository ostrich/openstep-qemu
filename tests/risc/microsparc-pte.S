/*
 * Standalone microSPARC-II PTE test ROM. No guest OS or disk.
 * SPDX-License-Identifier: GPL-2.0-or-later
 */
#ifndef LEAF_LEVEL
#define LEAF_LEVEL 1
#endif
#ifndef RESERVED
#define RESERVED 0xf8000000
#endif
.section .text
.global _start
_start:
    /* Copy to RAM at 16 MiB. With the MMU enabled VA 0 aliases that RAM.
     * Avoid modifying physical page 0 while executing in PROM boot mode. */
    set 0x70000000, %g1
    set 0x01000000, %g2
    mov 512, %g3
1:  lda [%g1] 0x20, %g4
    sta %g4, [%g2] 0x20
    add %g1, 4, %g1
    add %g2, 4, %g2
    subcc %g3, 4, %g3
    bne 1b
     nop
    set 0x10000, %g1
    set 0x1101, %g2
    st %g2, [%g1]
    set 0x11000, %g1
#if LEAF_LEVEL > 1
    set 0x1201, %g2
    st %g2, [%g1]
    set 0x12000, %g1
#endif
#if LEAF_LEVEL > 2
    set 0x1301, %g2
    st %g2, [%g1]
    set 0x13000, %g1
    /* The active instructions, data and report page must all be mapped. */
    set (RESERVED | 0x10008e), %g2
    st %g2, [%g1]
    set (RESERVED | 0x10018e), %g2
    st %g2, [%g1+4]
    set (RESERVED | 0x10028e), %g2
    st %g2, [%g1+8]
    set (RESERVED | 0x10038e), %g2
    st %g2, [%g1+12]
#else
    set (RESERVED | 0x10008e), %g2
    st %g2, [%g1]
#endif
    set 0x01002000, %g1
    set 0x13579bdf, %g2
    st %g2, [%g1]
    set 0x1000, %g1
    mov 0x100, %g2
    sta %g1, [%g2] 4
    clr %g1
    mov 0x200, %g2
    sta %g1, [%g2] 4
    mov 1, %g1
    sta %g1, [%g0] 4
    nop
    nop
    nop
    /* Instruction fetches above, ordinary data load/store, then a probe. */
    set 0x2000, %g1
    ld [%g1], %g2
    set 0x3000, %g3
    st %g2, [%g3]
    lda [%g1] 3, %g2
    st %g2, [%g3+4]
    set 0x50415353, %g2
    st %g2, [%g3+8]
2:  ba 2b
     nop
