# Game data formats

This document is the shared format notebook for the recompilation project and
the companion
[G-Police Blender](https://github.com/Tzeentchnet/G-Police-Blender) add-on. It
covers the USA PlayStation discs identified by
[disc_identity.json](../disc_identity.json). PC-version behavior is treated as
prior art, not assumed to be binary-compatible.

Last updated: **2026-11-04**

## Evidence policy

- **Verified** means a layout was checked across every reachable instance or
  against an exact header/hash.
- **Inferred** means the layout explains repeated size and relationship
  invariants but still needs a loader or renderer trace.
- **Unknown** fields must be preserved by tools and must not be normalized away.

Do not commit extracted retail records as test fixtures. Prefer synthetic
records and metadata-only inventories; let users point tools at their own disc
dump.

## Disc container

Both CUE files describe one track:

```text
TRACK 01 MODE2/2352
INDEX 01 00:00:00
```

The ISO9660 filesystem uses 2,048-byte logical sectors inside the 2,352-byte
raw sectors. XA and STR playback may depend on Mode 2 sector subheaders and
Form 2 payloads, so a generic 2,048-byte ISO file extraction is not sufficient
evidence for a round-trip media tool.

### Filesystem inventory

| Extension | Disc 1 count | Disc 1 bytes | Disc 2 count | Disc 2 bytes |
| --- | ---: | ---: | ---: | ---: |
| `.XA` | 91 | 257,974,272 | 91 | 283,320,320 |
| `.STR` | 11 | 273,891,328 | 12 | 246,996,992 |
| `.BIN` | 3 | 34,149,232 | 3 | 34,149,232 |
| Boot executable | 1 | 479,232 | 1 | 479,232 |
| `.RDA` | 1 | 34,768 | 1 | 34,768 |
| `.RDR` | 1 | 76 | 1 | 76 |
| `.RDT` | 1 | 69,386,756 | 1 | 69,386,756 |
| `SYSTEM.CNF` | 1 | 69 | 1 | 69 |

`BLANK2.BIN` is exactly 32 MiB of zero bytes on both discs. Its purpose is
unknown; preserve it as disc-layout data rather than treating it as an asset.

## PS-X EXE

Both disc boot files are byte-identical standard PS-X EXEs.

| Header field | Value |
| --- | --- |
| Magic | `PS-X EXE` |
| Entry PC | `0x8002E928` |
| Text load address | `0x80010000` |
| Text size | `0x00074800` |
| Stack pointer | `0x801FFFF0` |

The 2,048-byte PS-X EXE header is followed by the loaded body. The body occupies
`0x80010000` through `0x800847FF`.

## `FRONT.BIN` and `GAME.BIN`

These are game-specific loadable code/data modules, not PS-X EXEs.

| Property | `FRONT.BIN` | `GAME.BIN` |
| --- | --- | --- |
| Size | 213,004 (`0x3400C`) | 381,796 (`0x5D364`) |
| SHA-256 | `e183ee4377b69e65b023b7cc573e108580dea423618164c0d021d1fa298eca7d` | `07dad7905d0587f8b253b261c48f069da2c7bbf543ef36f4fce1fc3b32655f4b` |
| ISO sectors read | 105 | 187 |
| Load address | `0x80098B60` | `0x80098B60` |
| Exclusive end | `0x800CCB6C` | `0x800F5EC4` |
| Stable-read XOR32 | `0xEBCB7FCC` | `0xE31D4916` |
| Resident handoff | `0x8009DAE8` | `0x800B2A60` |

The resident loader uses the ISO directory's exact byte size, reads enough
2,048-byte sectors to cover it, requires repeated reads to have the same
32-bit-word XOR, copies exactly that byte size to `0x80098B60`, and flushes the
instruction cache. There is no module decompression, relocation stream, PS-X
EXE header, or hard-coded expected XOR in this path.

The two files are therefore verified mutually exclusive same-address modules.
The framework's page-aligned AOT records begin at `0x80098000`; their first
`0xB60` bytes are generated leading padding and are not part of either disc
file. Loading shorter `FRONT.BIN` after `GAME.BIN` does not clear the game-only
tail.

### `FRONT.BIN`

The file begins with:

```c
uint32_t export_count;      // 4
uint32_t export_pc[4];      // RAM addresses below
```

The four pointers are `0x8009A950`, `0x8009A9D4`, `0x8009A9E8`, and
`0x8009AA74`. The owned-input AOT profile preserves them as required dispatch
PCs without assuming that each is an independently discovered function
boundary. Static analysis found 203 function roots and 207 dispatch roots.
The file also contains front-end text, equipment descriptions, and STR paths.

### `GAME.BIN`

The file begins with module/debug metadata such as `Animation` and embedded
source paths before executable code. It is not a pure text segment beginning
at file offset zero. The verified AOT recipe currently carries 507 function
roots and 502 dispatch roots after title-declared entry enrichment.

The load address is a G-Police loader fact recorded in
[`aot/overlays.json`](../aot/overlays.json), not a convention that a general
disc parser should apply to unrelated `.BIN` files.

## `RDR2` archive selector

`RES.RDR` is 76 bytes and selects one RDT archive.

Verified layout:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 8 | ASCII `RDR2   ` plus NUL |
| `0x08` | 4 | Little-endian archive count (`1`) |
| `0x0C` | 64 | Archive-name slot; NUL-terminated `RES.RDT` followed by zero padding |

PC prior art uses repeated 64-byte archive-name slots. The PlayStation file has
only one slot and no `DISK1.RDT`/`DISK2.RDT` companions.

## `RDA2` index

Both the external `RES.RDA` and type-1 RDT payloads use the same exact framing:

```c
struct Rda2Index {
    char magic[8];       // "RDA2   \0"
    uint32_t max_slot_le;
    uint32_t entries_le[max_slot_le + 1];
};
```

For all 111 observed indexes (the external root plus 110 type-1 records):

```text
byte_size == 12 + 4 * (max_slot + 1)
```

The external root has:

- file size `0x87D0` (34,768);
- maximum slot `0x21F0` (8,688);
- slots `0..0x21F0`;
- exactly 8,689 entries.

Root entry distribution:

| Value/family | Count | Current interpretation |
| --- | ---: | --- |
| `0` | 2 | Null sentinel |
| `1` | 8,558 | Empty/control sentinel |
| `0x101` | 19 | Empty/control sentinel |
| low nibble `5` | 110 | Tagged local `RES.RDT` bank reference |

The value previously interpreted as nested-index metadata is slot zero. There
is no separate metadata word in the verified `RDA2` framing.

## Tagged record references

Verified record references use the low-nibble `5` family. The resolver masks
bits 2-5 and uses the result as a byte offset into its RDT handle table:

```text
reference_family = encoded_reference & 0x0F
handle_offset    = encoded_reference & 0x3C
handle_slot      = handle_offset >> 2
record_offset    = (encoded_reference & ~0x3F) >> 4
```

RDT record offsets are four-byte aligned, leaving encoded bits 2-5 available
for this selector. `RES.RDT` occupies handle slot 1, so its common local form
is:

```text
encoded_reference == (record_offset << 4) | 5
```

All 110 root references have low six bits `0x05` and select `RES.RDT`. Nested
indexes contain:

| Low six bits | Count | Interpretation |
| ---: | ---: | --- |
| `0x05` | 144,690 | Handle slot 1: local `RES.RDT` record |
| `0x15` | 5 | Handle slot 5; unresolved |
| `0x25` | 1 | Handle slot 9; unresolved |
| `0x35` | 1 | Handle slot 13; unresolved |

`RES.RDR` declares only the RDT used by handle slot 1. A parser must not clear
the selector and then treat the seven unavailable-selector references as local
offsets; doing so produces false bounds or self-reference failures.

The reader at `0x8003386C` demonstrates both operations directly: it masks the
reference with `~0x3F` before shifting by four for the file offset, and masks
with `0x3C` before indexing the RDT handle table.

Public PC-version tooling recognizes low-nibble tags `5`, `9`, and `D` as
selectors for `RES.RDT`, `DISK1.RDT`, and `DISK2.RDT`. That relationship is
useful prior art but only tag `5` is present in the verified PlayStation
resource graph.

## RDT record envelope

Every local record satisfies this envelope:

```c
struct RdtRecord {
    uint32_t self_ref_le;     // encoded reference, including handle selector
    uint32_t payload_size_le;
    uint32_t unknown_08_le;   // observed zero in every reachable record
    uint32_t class_word_le;    // low 16 bits zero; high 16 bits are class ID
    uint32_t relocation_count_le;
    uint8_t payload[payload_size_le];
    uint32_t relocation_offsets_le[relocation_count_le];
};
```

The payload starts at record offset `+0x14`. Each relocation offset addresses a
field within the payload. The loader reads that field's low 16-bit resource
slot, resolves it through the active nested `RDA2` bank, and replaces the field
with a runtime pointer.

The complete serialized span is:

```text
20 + payload_size + 4 * relocation_count
```

Records are referenced, not assumed to be stored contiguously. A parser must:

1. validate the reference family and handle selector before computing an
   offset;
2. bounds-check the 20-byte envelope;
3. require `self_ref` to match the incoming encoded reference;
4. bounds-check `payload_size`;
5. bounds-check the relocation tail and every relocation offset;
6. follow only known directory payloads;
7. detect duplicate references without duplicating extracted data.

The local graph contains 110 type-1 bank records and 144,690 unique
bank-contained records: 144,800 valid records across 19 class IDs. The seven
unavailable-selector entries are not included in that total.

## Known and candidate record types

| Type | Count | Status | Current interpretation |
| --- | ---: | --- | --- |
| `1 / 0x0001` | 110 | Verified | Nested `RDA2` bank index |
| `2 / 0x0002` | 708 | Unknown | Small 16-bit tables |
| `5 / 0x0005` | 1 | Unknown | One 4,866-byte table |
| `7 / 0x0007` | 11 | Inferred | Large raw 16-bit image/framebuffer data; one record is a valid TIM |
| `15 / 0x000F` | 67 | Verified | Standard `VAGp` audio samples |
| `25 / 0x0019` | 33,237 | Verified framing | Indexed texture planes |
| `27 / 0x001B` | 44,407 | Verified framing | RGB24 palettes |
| `29 / 0x001D` | 44,497 | Inferred | Fixed 32-byte texture descriptors |
| `612 / 0x0264` | 47 | Unknown | Exact semantic class not yet identified |
| `620 / 0x026C` | 18,642 | Verified identity | Principal geometry payload; multiple sub-layouts |
| `735 / 0x02DF` | 132 | Unknown | Offset-table records, possibly animation/assembly data |
| `1665 / 0x0681` | 903 | Unknown | Small fixed-layout records |
| `2496 / 0x09C0` | 10 | Unknown | Large table records |
| `2500 / 0x09C4` | 835 | Verified identity | `Artic`, serialized as 40-byte nodes |
| `2501 / 0x09C5` | 835 | Verified identity | `Shape`, serialized as recursive 20-byte nodes |
| `2684 / 0x0A7C` | 1 | Unknown | One 292-byte record |
| `2965 / 0x0B95` | 255 | Unknown | Four-byte records, all currently `1` |
| `3380 / 0x0D34` | 51 | Inferred | Associated with the `ObjCol` constructor |
| `3485 / 0x0D9D` | 51 | Inferred | Associated with the `ArnCol` constructor |

The candidate names are research priorities, not file extensions or stable
Blender API names.

## Type 15: VAG audio

All 67 type-15 payloads begin with `VAGp` and follow the conventional
big-endian VAG header. Observed sample rates include 22,050 Hz and 44,100 Hz.
For checked records:

```text
record payload size == 48-byte VAG header + declared VAG data size
```

Names such as `bang`, `radar`, and `warns` are present in the VAG name field.
A tool should use a tested VAG decoder rather than inventing a title-specific
audio interpretation.

## Type 25: indexed texture plane

Every type-25 payload begins with six little-endian 16-bit fields:

```c
struct TexturePlaneHeader {
    uint16_t version;       // always 1
    uint16_t width;
    uint16_t height;
    uint16_t color_count;   // observed <= 16 or 256
    uint16_t unknown_08;
    uint16_t unknown_0a;
};
```

The remaining bytes are index data:

- 33,143 records satisfy
  `payload_size == 12 + ceil(width * height / 2)` and use the <=16-color
  family, consistent with two 4-bit indices per byte.
- 94 records satisfy
  `payload_size == 12 + width * height`, use `color_count == 256`, and are
  consistent with one 8-bit index per pixel.

Observed dimensions:

- 16 x 16
- 32 x 16
- 32 x 32
- 64 x 16
- 64 x 32
- 64 x 64

Nibble order, row origin, transparency, and the two unknown header fields still
need renderer-backed confirmation.

## Type 27: RGB24 palette

All 44,407 type-27 payloads satisfy:

```c
struct PaletteHeader {
    uint16_t version;          // always 1
    uint16_t count_and_flag;   // low 15 bits are color count
};

uint8_t rgb[color_count][3];
```

And:

```text
payload_size == 4 + 3 * (count_and_flag & 0x7FFF)
```

The high bit is set in 9,613 records and clear in 34,794. Its meaning is
unknown. Most palettes contain 2-16 colors; four contain 256.

The byte order is structurally RGB triples, consistent with public PC tooling,
but color-space conversion and alpha/transparency rules remain to be verified
against rendered output.

## Type 29: texture descriptor

All 44,497 type-29 payloads are exactly 32 bytes. Their first two little-endian
16-bit values are width and height, and their dimension distribution matches
the type-25 texture families.

The remaining fields appear to associate texture, palette, and rendering
metadata, but their indices and flags are not yet proven. Exporters should not
rewrite these records. The Blender add-on can treat them as opaque descriptors
until cross-references are resolved.

## Type 620: geometry

Class `0x026C` is the principal geometry payload. The identity is supported by
Shape relocation targets and both renderer paths at `0x8005D880` and
`0x8005E504`.

The validated sub-layout starts with a 40-byte header:

```c
struct GeometryHeader {
    uint8_t unknown_00[8];
    uint8_t vertex_count;
    uint8_t polygon_count;
    uint8_t normal_count;
    uint8_t auxiliary_normal_count;
    uint8_t unknown_0c[4];
    uint16_t section_offsets_le[6];
    int16_t bounds_le[6];     // observed min x/y/z, max x/y/z
};
```

The first four section offsets identify the vertex, polygon, normal, and
auxiliary-normal sections. The last two sections and several header count bytes
remain unknown. A section may contain auxiliary tables after its counted
records, so section length is not itself a safe record count.

Vertices and the decoded normal families use eight-byte records:

```c
struct GeometryVector {
    int16_t x_le;
    int16_t y_le;
    int16_t z_le;
    uint8_t link_a;
    uint8_t link_b;
};
```

The meanings of the final two bytes differ by context and remain unknown.

Triangle and quad records have this variable-length layout:

```c
struct GeometryPolygon {
    uint8_t flags;
    uint8_t shading;
    uint8_t vertex_count;       // 3 or 4 in the validated layout
    uint8_t reserved;
    uint32_t material_ref_le;   // relocated; low 16 bits are a bank slot
    uint16_t normal_refs_le[vertex_count];
    uint8_t vertex_indices[vertex_count];
    uint8_t uv[vertex_count][2];
    uint8_t padding_to_4_bytes[];
};
```

The serialized size is:

```text
align4(8 + 5 * vertex_count)
triangle = 24 bytes
quad     = 28 bytes
```

Relocation entries point to polygon byte `+4`, where the material resource ID
is stored. Normal references can carry `0x4000` flag bits; their exact
interpretation remains unknown. Vertex indices are separate unsigned bytes and
must be checked against the header's total vertex count.

A strict corpus pass validates 11,074 of the 18,642 class-`0x026C` records.
The other 7,568 use different or still-undecoded layouts and must not be forced
through this parser.

Known validation fixture:

| Property | Value |
| --- | --- |
| Bank / slot | `611 / 614` |
| Encoded reference | `0x0203B905` |
| Vertices / polygons | `8 / 6` |
| Polygon topology | Six quads |
| Bounds | `(-2800, -2000, -3200)` to `(2800, 2000, 3200)` |
| Section offsets | `112, 184, 352, 400, 400, 412` |

## Types 2500 and 2501: Artic and Shape

Runtime class strings and constructors identify:

- class `0x09C4` as `Artic`, constructed by `0x80033BD0`;
- class `0x09C5` as `Shape`, constructed by `0x80034AD4`.

All 835 Shape payloads are multiples of 20 bytes. The constructor consumes
recursive nodes with this verified framing:

```c
struct ShapeNode {
    uint32_t cluster_argument_le;
    uint32_t child_count_le;
    uint32_t field_08_le;
    uint32_t resource_ref_le;   // relocated bank slot
    uint32_t field_10_le;
};
```

All 2,806 Shape relocations occur at offset `12 mod 20`, the
`resource_ref_le` field. Their resolved targets are:

| Target | Count |
| --- | ---: |
| Geometry `0x026C` | 1,968 |
| Unresolved/sentinel | 569 |
| Shape `0x09C5` | 103 |
| Artic `0x09C4` | 102 |
| Texture plane `0x0019` | 56 |
| Palette `0x001B` | 8 |

All 835 Artic payloads are multiples of 40 bytes and are recursively consumed
by the Artic constructor. Their field-level transform semantics are not yet
decoded, and the serialized records have no relocation tail.

## Type 7: raw images

The 11 type-7 records range from 5,120 to 614,400 bytes. Most look like raw
16-bit pixel planes. Some sizes correspond to common framebuffer dimensions,
but dimensions are not carried in the verified RDT envelope. One payload is a
structurally valid 16bpp TIM: its `0x10` magic, flags, and image-block length
are internally consistent. That does not make the entire type a TIM format.

Treat type 7 as a family requiring per-record context.

## XA and STR media

- `.XA` files are CD-XA audio streams used for music, radio, training, and
  briefings.
- `.STR` files multiplex PlayStation video sectors with CD-XA audio sectors.

Each raw sector is 2,352 bytes:

```c
struct XaRawSector {
    uint8_t sync[12];
    uint8_t header[4];
    uint8_t subheader[4];
    uint8_t subheader_copy[4];
    uint8_t sound_groups[18][128];  // audio sectors
    uint8_t unused[20];
    uint8_t edc[4];
};
```

The Mode 2 subheader supplies file number, channel number, submode, and coding
information. Relevant submode bits are:

- bit 6: real-time;
- bit 5: Form 2;
- bit 2: audio;
- bit 1: video.

The coding byte uses:

| Bits | Meaning |
| --- | --- |
| `1..0` | `0` mono, `1` stereo |
| `3..2` | `0` 37,800 Hz, `1` 18,900 Hz |
| `5..4` | `0` 4-bit ADPCM, `1` 8-bit ADPCM |
| `6` | emphasis |

Each 128-byte sound group contains 16 parameter bytes and 112 interleaved
sample bytes. Four-bit modes contain eight 28-sample sound units; eight-bit
modes contain four. Parameters are duplicated inside the group and select the
range plus one of four predictor pairs:

```text
K0 = 0, 240, 460, 392
K1 = 0,   0, -208, -220
predictor divisor = 256
```

Decoded samples per sector, per channel:

| Source coding | Mono | Stereo |
| --- | ---: | ---: |
| 4-bit | 4,032 | 2,016 |
| 8-bit | 2,016 | 1,008 |

Files can interleave multiple file/channel streams. Stream identity therefore
includes ISO path, subheader file number, channel number, and coding byte. The
companion add-on's Disc 1 scan identifies 1,211 such combinations across XA
and STR files and can decode an individual combination to 16-bit PCM WAV.

A raw export must preserve complete 2,352-byte sectors, including sector order,
duplicated subheaders, coding parameters, and interleave. STR video-frame
decoding remains unsupported; raw STR sector export is lossless.

## Blender add-on contract

The add-on should have separate layers:

1. **Container reader:** `RDR2`, `RDA2`, tagged references, and RDT envelopes.
2. **Resource decoders:** one module per verified type.
3. **Semantic scene layer:** meshes, materials, transforms, animations, and
   names only after their relationships are proven.
4. **Blender adapter:** coordinate conversion and datablock creation, with no
   archive parsing hidden in UI operators.

The current implementation in
[Tzeentchnet/G-Police-Blender](https://github.com/Tzeentchnet/G-Police-Blender)
covers the container layer, the strict class-620 mesh variant, Shape/Artic
reference traversal, raw XA/STR sector export, and XA-to-WAV decoding. Texture
pixels, Artic transforms, unsupported geometry variants, and STR video frames
remain deliberately unimplemented.

Recommended stable identity for an asset:

```text
disc identity + root bank slot + resource slot
    + handle selector + RDT record offset + class ID
```

The RDT offset is the deduplicated record identity. Bank and resource slots
preserve graph provenance and are required to interpret raw 16-bit relocation
IDs.

### Import-first policy

Archive handling remains read-only:

- enumerate indexes and records;
- decode type-25 planes and type-27 palettes;
- associate type-29 descriptors without modifying them;
- import only class-620 geometry that passes the strict structural validator;
- identify and decode XA audio or preserve complete raw sectors;
- preserve all unknown fields and raw bytes in memory.

Exporting derived meshes, images, PCM audio, metadata, or unmodified raw sectors
does not alter the archive and is safe. Do not offer RDA/RDT rewrite or repack
until the game can reload a synthetic or user-modified record and the following
are known:

- all geometry sub-layouts and alignment rules;
- texture-descriptor, palette, transparency, and texture-page relationships;
- transform hierarchy and pivot rules;
- archive size/alignment, relocation, and index rewrite rules;
- behavior of unavailable handle selectors when companion RDT files are
  absent.

### Parser safety

Retail files are untrusted parser input. The add-on must:

- reject out-of-range counts, offsets, and payload sizes;
- cap allocations before reading payloads;
- detect cycles and excessive recursion;
- never use asset names as unsanitized output paths;
- avoid extracting outside a user-selected directory;
- report unsupported records rather than silently skipping or guessing.

## Public prior art

[apemax/GPModTools](https://github.com/apemax/GPModTools) is a GPL-3.0 project
for the PC version of G-Police. Its public tools:

- extract PC `.RDT` archives through `.RDR`, `.RDA`, `.RDI`, and `.RDX`
  metadata;
- convert PC `.img` images;
- combine PC `.tex`, `.pal`, and `.bmp` texture components.

Useful cross-version observations include the 20-byte RDT envelope, tagged
archive references, RGB palette triples, and indexed texture families.

Important differences:

- the PlayStation disc has no `.RDI` or `.RDX` files;
- the PlayStation root selects only `RES.RDT`;
- PlayStation semantic type IDs and rendering rules still need independent
  verification;
- GPModTools code is GPL-3.0 and should not be copied into a differently
  licensed add-on without an explicit licensing decision.

This document records independently checked PlayStation invariants so the
Blender implementation can be written against a clear project-owned
specification.

## Research backlog

1. Resolve how type-29 descriptors reference type-25 and type-27 records.
2. Render decoded texture/palette pairs and establish nibble order, row origin,
   transparency, and color conversion.
3. Classify and decode the 7,568 unsupported class-620 variants.
4. Decode the remaining geometry sections, normal-reference flags, header
   fields, UV page selection, and source unit scale.
5. Decode Artic transforms, pivots, and Shape instancing.
6. Map type 735 and the remaining fields in the 2500/2501 pair.
7. Determine the serialized roles of the `ObjCol`/`ArnCol`-associated
   3380/3485 classes and identify collision/mission data.
8. Decode STR video frames while preserving their multiplexed XA streams.
9. Compare a legally owned PC install at the metadata level without assuming
   format parity.
10. Expand synthetic fixtures to cover handle selectors, relocation failures,
    unsupported geometry variants, and XA coding modes.
