# Architecture

This document records how the current title project and the original game fit
together. It deliberately separates verified metadata from tool-assisted
inference.

Last updated: **2026-11-04**

## Evidence labels

- **Verified:** directly encoded in a committed config, executable header,
  exact hash, or repeatable parser invariant.
- **Inferred:** strongly supported by code/data relationships or framework
  discovery, but not yet confirmed with a runtime trace or loader
  disassembly.
- **Hypothesis:** a useful direction that still needs a falsifiable test.

## Project layers

```text
owned CUE/BIN + owned SCPH5552 BIOS
                  |
                  v
scripts/gpolice_psxrecomp_cli.py
                  |
                  v
       pinned PSXRecomp CLI and emitters
          |              |                    |
          v              v                    v
 generated resident C  generated BIOS C  audited module C
          |              |               (aot/overlays.json)
          +--------------+--------------------+
                         v
                psx-runtime executable
                         |
             +-----------+------------+
             |                        |
             v                        v
      resident native dispatch  guarded module dispatch
                                (static AOT/interpreter)
```

The title adapter exists only because the current upstream CLI hard-codes the
SCPH1001 retail generation path. All normal disc preparation and game-code
emission remain upstream behavior. See [UPSTREAM.md](UPSTREAM.md).

## Build modes

### Setup host

When the generated dispatch marker is absent, or
`PSXRECOMP_FORCE_SETUP_HOST` is enabled, CMake builds a first-run host. It
contains the launcher and code-generation host but may contain no generated
game or retail BIOS code. The user selects owned inputs and the host rebuilds
the full target locally.

### Full runtime

The full target links:

- the PSXRecomp runtime;
- the recomp-ui launcher;
- the generated SCPH5552 BIOS backend;
- 33 generated resident-game translation units;
- the generated resident dispatch table; and
- an ignored, owned-input-generated static dispatcher plus one translation
  unit for each verified runtime module.

Generated retail-derived code remains local and ignored.

## Original disc organization

Both discs are single-track `MODE2/2352` images with ISO9660 filesystems.

| Property | Disc 1 | Disc 2 |
| --- | ---: | ---: |
| Serial | `SLUS-00544` | `SLUS-00556` |
| ISO files | 110 | 111 |
| Logical file bytes | 635,915,733 | 634,367,445 |
| XA files | 91 | 91 |
| STR files | 11 | 12 |

The discs contain byte-identical copies of the resident executable, code
modules, and core resource set:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `SLUS_005.44` / `SLUS_005.56` | 479,232 | `100f7bfee0f2d48e55dc139b25fc5c2701024ff3aa312270c7be2e2d5be6ce11` |
| `FRONT.BIN` | 213,004 | `e183ee4377b69e65b023b7cc573e108580dea423618164c0d021d1fa298eca7d` |
| `GAME.BIN` | 381,796 | `07dad7905d0587f8b253b261c48f069da2c7bbf543ef36f4fce1fc3b32655f4b` |
| `RES.RDR` | 76 | `d948cb9e118e09802cb24c1af82a4d7cec3f05823abf0cd1443af85114677fe9` |
| `RES.RDA` | 34,768 | `12bd741696a59c19622d50a691a2e7e998ed03ed563fbb0e9126787f011e3579` |
| `RES.RDT` | 69,386,756 | `f604fc40ffd52ab345ab70f38c8e8c4101efd029ca010b9e43e89afccd6531cc` |

The major disc split is media:

- Disc 1 carries `CAM1A.STR` through `CAM3A.STR`, `STR1A.STR`,
  `STR2A.STR`, `INTA.STR`, `INTH.STR`, and `HORTA.STR`.
- Disc 2 carries `CAM4A.STR` through `CAM7A.STR`, `STR3A.STR` through
  `STR6A.STR`, and `OUTA.STR`.
- Briefing XA paths exist on both discs, but the long mission-specific entries
  are divided between them.

`FRONT.BIN` contains strings for movie paths from both discs. Combined with the
identical code modules, this supports a single program that selects media
according to campaign state and mounted disc.

## Resident executable

The boot file is a standard PS-X EXE. The two differently named disc files are
byte-identical.

| Field | Value | Evidence |
| --- | --- | --- |
| Load address | `0x80010000` | Verified PS-X EXE header |
| Entry PC | `0x8002E928` | Verified PS-X EXE header |
| Text/body size | `0x00074800` | Verified PS-X EXE header |
| Resident body end | `0x80084800` | Derived from header |
| Configured stack | `0x801FFFF0` | Verified title config |
| SYSTEM.CNF stack | `0x80200000` | Verified disc file |

The 16-byte difference between the configured stack top and `SYSTEM.CNF` is
the expected alignment below the top of 2 MiB RAM, not evidence of another RAM
region.

The curated seed file contains 874 addresses. Current generation expands that
to 1,438 emitted function bodies across 33 C shards. The dispatch table also
contains exact continuation and internal-entry rows, so its row count is much
larger than the function count.

### Resident control-flow partitions

The seven generation warnings are now classified. Five are transfers between
pieces of three larger routines:

- `0x80041DE8-0x80042134`, including a jump over a fallback initialization
  block and a loop back to `0x80041F3C`;
- `0x80042FD0-0x800431B8`, a 176-byte-stack routine whose save sequence
  continues through `0x80042FFC` and whose loop crosses `0x80043058`,
  `0x80043068`, and `0x800430E8`; and
- `0x8006A3A0-0x8006A3D8`, a linked-structure search with an early exit and a
  back edge.

The other two warnings decode unreachable words as jumps: one follows the
terminal B0(38h) BIOS thunk at `0x80030008`, and one occupies the eight-byte
gap at `0x8004A9E4-0x8004A9EC`. Neither target lies in the resident image.

There are no warning-backed callable entries to add. In particular,
`0x80042FFC` and `0x80043068` are interior addresses, so they were removed from
the seed file. Automatic split discovery still emits the required continuation
entries and preserves the existing dispatch output.

### Embedded source provenance

The binary contains development-time source paths. These strings do not provide
source code, but they reveal subsystem boundaries.

Resident paths include:

- `ARENA.c`
- `DISPLAY.c`
- `HEAPLLOC.c`
- `INIT3D.c`
- `MATRIX.c`
- `SHADING.c`

This supports a resident shell containing memory management, display/GPU
support, foundational 3D math, and shared rendering services.

## Runtime-loaded modules

The resident loader contract is now statically verified. Both modules are
copied verbatim into the same destination and therefore form mutually
exclusive overlays:

| Module | Mode | File size | Destination | Exclusive end | Sectors | Stable XOR32 | Resident handoff |
| --- | ---: | ---: | --- | --- | ---: | --- | --- |
| `FRONT.BIN` | 0 | 213,004 | `0x80098B60` | `0x800CCB6C` | 105 | `0xEBCB7FCC` | `0x8009DAE8` |
| `GAME.BIN` | 1 | 381,796 | `0x80098B60` | `0x800F5EC4` | 187 | `0xE31D4916` | `0x800B2A60` |

`func_8001F904(mode)` selects `\FRONT.BIN;1` for mode 0 and
`\GAME.BIN;1` for mode 1. It reads the destination through the resident word
at `0x80011D20`, whose value is `0x80098B60`, then calls the retry wrapper
`func_8001F4A0`.

The worker `func_8001F4E4`:

1. resolves the ISO9660 file and uses its exact byte size;
2. reads `ceil(size / 2048)` sectors;
3. computes the XOR of its 32-bit words with `func_8001FB4C`;
4. requires repeated reads to produce the same XOR, using separate front/game
   flags and saved values at `0x800731C0-0x800731CC`;
5. retries up to ten times;
6. copies exactly the ISO file size to `0x80098B60` with BIOS `memcpy`; and
7. flushes the instruction cache.

The XOR is a repeat-read consistency check, not a comparison with a compiled-in
expected digest. Because the copy is exact-sized, loading shorter `FRONT.BIN`
after `GAME.BIN` leaves the old game bytes above `0x800CCB6C` untouched. No
current evidence shows those stale bytes are called while the front module is
active.

`func_8001FE50` calls the front loader at `0x80020040`, then calls
`0x8009DAE8` with `a0 = 0` at `0x80020058`. Its gameplay path calls the game
loader at `0x8002008C`, then calls `0x800B2A60` at `0x800200A4`.

A 2026-11-04 Disc 1 interactive smoke followed the normal campaign path into a
live mission and observed guarded native `GAME.BIN` dispatch. This confirms
that an ordinary gameplay flow reaches the `0x800B2A60` handoff and executes
the audited static variant; it does not prove complete indirect-entry coverage
or mission behavior.

`FRONT.BIN` begins with a four-entry pointer table and contains menus, campaign
text, equipment descriptions, and all known STR movie paths. Its four table
targets are `0x8009A950`, `0x8009A9D4`, `0x8009A9E8`, and `0x8009AA74`.

`GAME.BIN` contains embedded paths naming gameplay subsystems:

- `ANIMS.c`
- `BOMB.c`
- `CAR.c`
- `CIVCAR.c`
- `CRAFTYPE.c`
- `ENEMY1.c`
- `EPP.c`
- `FLARE.c`
- `FLIGHT.c`
- `GYRO.c`
- `LASER.c`
- `MISSILE.c`
- `PLASMA.c`
- `SIEGEGUN.c`
- `TURRETS.c`
- `WEAPON.c`

The file begins with module/debug metadata and strings before executable code;
it is not a raw code blob starting at offset zero.

### Owned-input native module generation

[The AOT profile](../aot/overlays.json) contains only disc identities, loader
evidence words, hashes, sizes, addresses, and entry metadata. It accepts either
USA disc because both carry byte-identical modules, excludes those two files
from heuristic generic extraction, verifies their complete byte extents, and
publishes guarded C only under the ignored `generated/` directory.

The current profile run produced two verified recipes and three C translation
units: the dispatcher and one unit per module. The compiler reported:

| Module | Function roots | Dispatch roots | Static discovery roots | Recompiled functions |
| --- | ---: | ---: | ---: | ---: |
| `FRONT.BIN` | 203 | 207 | 141 | 204 |
| `GAME.BIN` | 507 | 502 | 396 | 507 |

Continuation-passing resume coverage adds 19,090 guarded wrappers, for 19,801
audited static variants in total. The audit verified that every guard matches
the known original-disc input and that both resident handoffs and all four
front export-table PCs are present. It deliberately reports
`full_static_coverage_proven = false`: static discovery is strong coverage, not
proof that every possible indirect entry has been found, so misses still fall
back to the dirty-RAM interpreter.

A bounded headless Disc 1 run reached the front handoff once and recorded more
than ten million guarded static hits in the module address range. The
2026-11-04 interactive smoke subsequently reached the game handoff and
recorded sustained guarded static dispatch during live mission rendering and
control. Neither observation changes the audit's conservative
`full_static_coverage_proven = false` result.

## Resource system

The core resource chain is:

```text
RES.RDR -> RES.RDT
RES.RDA -> root RDA2 index
RES.RDT -> tagged records and nested RDA2 indexes
```

The resident executable contains the strings `.RDR`, `RDR2`, `.RDA`, `RDA2`,
and `Shape`, showing that this is a native game resource system rather than an
ISO naming convention.

Verified structural findings:

- `RES.RDR` declares one RDT archive named `RES.RDT`.
- `RES.RDA` stores maximum slot `8,688`, followed by entries for slots
  `0..8,688`: 8,689 entries in total.
- Its 110 local references resolve to type-1 bank records in `RES.RDT`; one
  valid reference is the value `5`, which addresses the record at byte zero.
- Each type-1 payload is another exact `RDA2` index. Its resource references
  are global `RES.RDT` offsets, not offsets relative to the bank record.
- Verified record references use the low-nibble `5` family. Bits 2-5 select an
  RDT handle-table entry, and the record offset is
  `(reference & ~0x3F) >> 4`.
- The declared `RES.RDT` contains 144,690 unique bank-contained resources.
  Including the 110 type-1 bank records gives 144,800 valid local records
  across 19 type IDs.
- Seven nested entries use unavailable selectors (`0x15`, `0x25`, or `0x35`
  in the low six bits, selecting handle slots 5, 9, and 13). Because
  `RES.RDR` declares no corresponding RDTs, they are unresolved rather than
  local `RES.RDT` records.
- Every local record repeats its tagged reference and declares its payload
  size, class ID, and relocation count. A relocation tail identifies payload
  fields whose 16-bit bank slot IDs are replaced with runtime pointers.

The verified asset path is:

```text
root RDA2 slot
    -> type-1 bank record
        -> nested RDA2 resource slot
            -> Shape (0x09C5) / Artic (0x09C4)
                -> geometry (0x026C)
                    -> material and texture-family resources
```

Runtime constructor and renderer traces promote several former candidates:

- class `0x09C4` is `Artic` and uses 40-byte serialized nodes;
- class `0x09C5` is `Shape` and uses recursive 20-byte nodes;
- class `0x026C` is the principal geometry payload;
- classes `0x0019`, `0x001B`, and `0x001D` are the indexed texture plane,
  RGB24 palette, and texture-descriptor families respectively.

The strict geometry layout currently validates 11,074 of the 18,642 class
`0x026C` records. The remaining 7,568 are preserved and reported as unsupported
variants rather than decoded by guesswork.

The high record count reflects the game's indexed resource graph, not 144,800
ISO files. Asset names are not present in the PlayStation disc set in the same
form as the known PC tooling.

See [FORMATS.md](FORMATS.md) for byte layouts and the current semantic map.

## Runtime execution model

Resident PCs use generated native dispatch when an exact translated entry is
available. Runtime-loaded or modified RAM does not automatically match the
resident image.

With `overlay_cache = true`:

1. unknown executable RAM can run through the dirty-RAM interpreter;
2. the linked static dispatcher checks current code bytes before using a
   matching `FRONT.BIN` or `GAME.BIN` native variant;
3. runtime observations can still be recorded as private overlay captures;
4. matching uncovered regions can be compiled into guarded local cache shards
   when a toolchain is present; and
5. any remaining gap falls back to interpretation.

The setup and source-generation paths build the static variants from the
player's owned disc. The generated C, private captures, module binaries, and
BIOS bytes remain ignored and are not release-source inputs.

## Open architecture questions

- What consumes the four `FRONT.BIN` header pointers beyond their verified
  dispatch role?
- Can any front-end path reach stale `GAME.BIN` tail bytes left above
  `0x800CCB6C`, or are all calls constrained to the active module?
- How do type-29 texture descriptors associate type-25 image planes and
  type-27 palettes, including transparency and texture-page selection?
- What distinguishes the 7,568 class-`0x026C` records that do not match the
  validated triangle/quad layout?
- What are the remaining geometry sections, normal-reference flag bits, and
  header count fields?
- How do Artic nodes encode transforms, pivots, and repeated Shape instances?
- What source coordinate system and fixed-point unit scale should the Blender
  adapter expose? The current `(x, -z, -y) * 0.001` conversion is an importer
  convention, not a proven game-space unit definition.
- Which types represent animation, collision, mission, and higher-level scene
  data? Constructor evidence currently associates `0x0D34` and `0x0D9D` with
  `ObjCol` and `ArnCol`, but their serialized semantics remain incomplete.
- Does the campaign change discs through a standard CD-ROM swap path or a
  title-specific front-end transition?

Each answer should be added with its evidence and reproduction method rather
than replacing an inference silently.
