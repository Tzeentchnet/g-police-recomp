# Development log

This log preserves useful history from the standalone setup candidate while
separating it from the current, substantially expanded project.

## Inherited project-basis history

### 2026-09-06 - Portable setup recipe

The upstream project basis prepared a portable owned-input setup recipe from
framework `00a8ae0051e85c7d07ceb6c0a7bea9a315f8c476`. The snapshot retained
title configuration and seed addresses, added the bounded setup path, and
excluded private retail inputs and generated outputs. Native CI and Windows
package acceptance remained pending.

### 2026-09-07 - Native canary and dependency provenance

The setup candidate incorporated the existing C-linkage correction and pinned
recomp-ui portable-tool wording fix. It recorded complete identities for the
framework, launcher, recomp-net, and rbengine dependencies. This changed build
and package provenance rather than guest runtime behavior.

## Current project history

### 2026-11-04 - Rebase onto maintained PSXRecomp

Rebased from the setup candidate's PSXRecomp pin `bca3aa8` to maintained
PSXRecomp `060ef0ab` (`v0.3.4-alpha-28-g060ef0ab`). Canonical submodule URLs
now point to the RetroPortingToolKit repositories. Nested framework pins were
updated, and recomp-ui advanced to compatible revision `dd47b18`.

Enabled the current overlay-cache path and added a title-level configure guard
so the first-run setup host can exist before local BIOS and game generation.
A title-owned CLI adapter now honors the configured SCPH5552 BIOS profile while
delegating disc preparation and code emission to the pinned upstream CLI.

Both supplied USA disc images were re-probed and matched the committed sizes,
hashes, serials, executable identity, and fingerprints. The current emitters
generated the SCPH5552 backend and 33 resident game-code shards. Clean Windows
setup-host and full-runtime builds passed, followed by self-checks and bounded
headless starts with Disc 1 (`SLUS-00544`) and Disc 2 (`SLUS-00556`).

### 2026-11-04 - Architecture and format baseline

Reframed the repository as an active development project rather than a static
release candidate. Added living documentation for architecture, game formats,
validation, and findings suitable for upstream PSXRecomp work.

An ISO9660 inventory found 110 files on Disc 1 and 111 on Disc 2. Both discs
carry byte-identical resident executables, `FRONT.BIN`, `GAME.BIN`, `RES.RDR`,
`RES.RDA`, and `RES.RDT`; their movie sets and mission-briefing XA lengths
differ.

PSXRecomp's play-free generic overlay detector recovered `FRONT.BIN` and
`GAME.BIN` at the same inferred file base, `0x80098B60`, confirming that the
front-end and gameplay modules occupy a mutually exclusive RAM region. The
detector found 203 candidate function entries in `FRONT.BIN` and 502 in
`GAME.BIN`. These are discovery results, not yet an audited AOT overlay
profile.

The resource graph was parsed structurally without extracting retail assets:

- `RES.RDR` selects one archive, `RES.RDT`.
- `RES.RDA` is an exact `RDA2` array with 8,688 entries.
- Tagged references resolve to 144,800 valid records across 19 observed type
  IDs with no bounds or self-reference failures.
- Type 1 records are nested `RDA2` directories.
- Type 15 records are standard `VAGp` samples.
- Type 25 records contain indexed texture planes.
- Type 27 records contain RGB24 palettes.
- Type 29 records are fixed-size texture descriptors whose dimensions match
  the texture families.

Public PC-version prior art in
[apemax/GPModTools](https://github.com/apemax/GPModTools) was reviewed and is
credited in the format notes. Its GPL-3.0 implementation and PC-specific
`RDI`/`RDX` assumptions are not copied into this project.

### 2026-11-04 - Windows setup-package acceptance

Accepted a local `0.1.1` Windows owned-input setup package against the frozen
source and framework identities. The package excludes retail BIOS bytes,
OpenBIOS, generated game code, player state, framework test fixtures, and
local overlay-toolchain state while retaining the current bundled mod catalog.

The 31,214,833-byte archive passed the payload and platform-copy audits. Both
packaged recompiler emitters passed native `--help` smoke tests from a fresh
path containing spaces. Extracting the archive into a new source tree,
configuring with no generated game or BIOS backend, and rebuilding
`G_Police_Recompiled.exe` also passed with version stamp `0.1.1`.

The existing MinGW `.rsrc merge failure: multiple non-default manifests`
diagnostic reproduced during the clean archive rebuild and remains tracked as
a separate release blocker.

### 2026-11-04 - Windows manifest conflict resolved

Minimized the MinGW resource warning to GCC 16.2's automatic
`default-manifest.o` end file. It added a 599-byte long-path manifest beside
PSXRecomp's 2,101-byte UTF-8 manifest, leaving two type-24 resources with the
same ID and language. The title now supplies one combined manifest and derives
a target-local GNU specs override that removes only the injected default
manifest.

Both setup-host and generated full-runtime links complete without the resource
merge diagnostic. Each resulting PE contains one ID-1/en-US manifest with
UTF-8, long-path, supported-OS, and `asInvoker` declarations, plus six icon
images and one icon-group resource.

### 2026-11-04 - Resident transfer warnings classified

Captured all seven resident-code generation warnings in an isolated output
tree and traced each warning block to its actual MIPS terminator, destination,
and unsplit parent routine. Five are valid shared continuations across emitted
function pieces. Two decode unreachable words after a terminal BIOS thunk or
between real functions. No warning identifies a missing callable entry, jump
table, or unsupported instruction.

Removed the proven interior seeds `0x80042FFC` and `0x80043068`. Regeneration
with 874 seeds still produced 1,438 functions, 33 shards, and byte-identical
dispatch output; automatic discovery recreates the needed continuation pieces.

Added a retail-free synthetic PS-X EXE reproducer for both warning shapes. It
also verifies the underlying generic issue: the emitter already generates
terminating CPS transfers. A reachable continuation then receives an
unreachable next-function call, while an unreachable data block reports
`emitting fallthrough` without actually emitting that call.

### 2026-11-04 - Runtime module loader and native AOT audit

Traced the resident path for `FRONT.BIN` and `GAME.BIN` from filename
selection through ISO lookup, repeat-read XOR validation, exact-size BIOS
`memcpy`, instruction-cache flush, and resident-to-module handoff. Both files
load verbatim at `0x80098B60`; front enters at `0x8009DAE8`, gameplay at
`0x800B2A60`. The shorter front load intentionally leaves any prior game-only
tail bytes untouched.

Added a metadata-only original-disc AOT profile that accepts either USA disc,
pins both complete module extents by SHA-256, verifies resident loader words,
and preserves the four `FRONT.BIN` export-table dispatch PCs. Generate now
publishes ignored guarded static C from the player's own disc and CMake links
the dispatcher plus one translation unit per module.

The production pipeline verified two images and two recipes, with every guard
matching the known original-disc bytes. It emitted 19,801 audited variants
with no failed or skipped shard. A full Windows runtime build linked all three
translation units. A bounded Disc 1 debug probe then hit the front handoff and
recorded more than ten million guarded static dispatches. The game handoff was
not reached without menu input and remains part of interactive acceptance.

Linking also exposed a generic high-level CMake argument-order bug:
`GAME_OVERLAY_STATIC_C` is swallowed when written after `GEN_FULL_GLOB`.
The title keeps the forwarded keyword before that multi-value argument and
records the upstream candidate as U-008.
