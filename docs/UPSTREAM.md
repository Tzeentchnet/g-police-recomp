# Upstream findings

This is a living ledger for findings that may be useful to
[RetroPortingToolKit/psxrecomp](https://github.com/RetroPortingToolKit/psxrecomp)
or [RetroPortingToolKit/recomp-ui](https://github.com/RetroPortingToolKit/recomp-ui).
It is not an issue tracker and does not imply that upstream has accepted a
problem statement.

Baseline reviewed: PSXRecomp
`060ef0ab34a27ab9c35ad92f52f573e8cea22086` and recomp-ui
`dd47b1887b1858473bb42c38f4307f0eb1b07e60`.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Confirmed | Reproduced in a clean title flow with the pinned upstream |
| Needs minimization | Observed, but a small upstream-only reproduction is still required |
| Design question | Behavior is real, but the desired generic policy needs agreement |
| Title-specific | Keep local unless evidence shows a reusable framework need |
| Filed | An upstream issue or pull request exists and should be linked |

No finding below has been filed yet.

## Candidate summary

| ID | Priority | Status | Area | Finding |
| --- | --- | --- | --- | --- |
| U-001 | High | Confirmed | CLI/codegen | Retail BIOS generation ignores the configured BIOS profile and hard-codes SCPH1001 |
| U-002 | High | Confirmed | CMake/setup host | The zero-BIOS setup-host decision occurs after the file-scope BIOS fatal check |
| U-003 | Medium | Design question | Dependency contract | PSXRecomp and recomp-ui API compatibility is not expressed as a version/pin constraint |
| U-004 | Medium | Confirmed | Windows resources | GCC 16 WinLibs injects `default-manifest.o` beside the framework manifest |
| U-005 | Low | Confirmed | Function discovery | Explicit split transfers still emit dead fallthrough calls and warnings |
| U-006 | Low | Title-specific | Overlay discovery | `FRONT.BIN` and `GAME.BIN` need a verified same-address title profile |
| U-007 | Medium | Confirmed | Setup packaging | The staged-source audit treats `if(NOT EXISTS ...)` probes as required files |

## U-001: Profile-driven retail BIOS generation

**Status:** Confirmed
**Local workaround:** [the title CLI adapter](../scripts/gpolice_psxrecomp_cli.py)

### Observation

The generic CLI exposes `[recompiler] bios_config`, and the runtime is capable
of linking arbitrary generated BIOS stems. The retail-BIOS path in
[`psxrecomp_cli.py`](../psxrecomp/psxrecomp_cli.py), however:

- stages every supplied dump as `bios/SCPH1001.BIN`;
- probes only the `SCPH1001` backend;
- regenerates only `bios/SCPH1001.toml`;
- tells users to pass `SCPH1001.BIN`.

G-Police selects `bios/SCPH5552.toml`, whose `[program].rom` path is
`bios/EUR-PSX-SCPH5552.bin`. The generic path therefore generates or checks the
wrong backend.

### Impact

Any title requiring a retail profile other than SCPH1001 needs a local wrapper
or a pre-staged framework tree. The setup wizard appears profile-aware at the
title level but fails during generation.

### Proposed upstream shape

1. Resolve the configured profile from `[recompiler] bios_config`.
2. Derive the stem from the profile name.
3. Read the profile's `[program].rom` destination.
4. Stage the user dump there.
5. Probe and regenerate that stem.
6. Preserve current SCPH1001 behavior when no profile is configured.

### Acceptance tests

- Existing SCPH1001 generation remains unchanged.
- A synthetic custom profile stages to its declared ROM path.
- Backend-presence checks use the custom stem.
- Missing custom profiles and ROM paths fail explicitly.
- CLI help describes profile-driven behavior rather than SCPH1001.

The local tests in
[`tests/test_codegen_cli_bios.py`](../tests/test_codegen_cli_bios.py) provide a
starting title-level regression set but should be replaced with upstream-owned
synthetic fixtures in a pull request.

## U-002: Setup-host BIOS check ordering

**Status:** Confirmed
**Local workaround:** The pre-include guard in
[`CMakeLists.txt`](../CMakeLists.txt)

### Observation

[`runtime/runtime.cmake`](../psxrecomp/runtime/runtime.cmake) builds the BIOS
registry and fails when no generated backend exists while the file is being
included. Later, `psxrecomp_add_game_runtime()` checks whether the generated
game marker exists and sets `PSXRECOMP_ALLOW_NO_BIOS=ON` for a setup host.

The later inference cannot affect the earlier fatal check. A clean title
checkout therefore has to set `PSXRECOMP_ALLOW_NO_BIOS` before including
`runtime.cmake`, even though the high-level helper already has setup-host
logic.

### Impact

The advertised high-level title helper is not sufficient for a first-run setup
host on a clean tree. Each affected title needs ordering knowledge from the
framework internals.

### Proposed upstream shape

Possible approaches:

- move the no-backend fatal check until the first runtime target is declared;
- split registry discovery from registry validation and let the high-level
  helper select setup/full mode first; or
- expose a small pre-include setup-host helper and use it in generated title
  scaffolds.

The preferred change should keep a full runtime strict: a build that claims to
contain game code must still fail when every requested BIOS backend is absent.

### Acceptance tests

- A clean setup-host fixture configures without generated BIOS code.
- A full-runtime fixture with no generated BIOS still fails.
- A generated custom retail stem links and appears in the registry.
- Reconfiguration from setup host to full runtime does not retain a stale
  permissive cache value.

## U-003: PSXRecomp/recomp-ui compatibility contract

**Status:** Design question

### Observation

Advancing PSXRecomp while retaining the setup candidate's older recomp-ui pin
produced compile failures for launcher structures and fields used by the
current runtime. Advancing recomp-ui to `dd47b18` resolved the mismatch.

The two repositories are independently pinned, but the compatible range is not
machine-readable at the title boundary.

### Possible upstream work

- publish a minimum recomp-ui revision or API version in PSXRecomp;
- expose a `RECOMP_UI_API_VERSION` compile definition and fail with a focused
  configure-time message;
- provide a dependency-pair manifest in project scaffolding and release docs.

This is not a current runtime bug once compatible revisions are used. The value
would be a faster, clearer failure for title maintainers.

## U-004: MinGW manifest merge diagnostic

**Status:** Confirmed
**Local workaround:** The title manifest and target-local GNU specs override in
[the title CMake file](../CMakeLists.txt)

### Observation

Both setup-host and full-runtime links print:

```text
.rsrc merge failure: multiple non-default manifests
```

The reproducing toolchain is GCC 16.2.0, GNU ld/windres
2.47.20260726, CMake 4.4.4, and Ninja 1.13.2. The link contains only the
PSXRecomp manifest resource object and the title icon object; recomp-ui
correctly refrains from adding its own manifest.

GCC's `*endfile` spec adds
`%{!shared:%:if-exists(default-manifest.o%s)}`. The WinLibs
`default-manifest.o` supplies a 599-byte ID-1 manifest with
`longPathAware=true`. PSXRecomp supplies a 2,101-byte ID-1 manifest with the
UTF-8 active code page, supported-OS declarations, and execution level. GNU ld
keeps both duplicate type-24/ID-1 entries and emits the diagnostic.

The local workaround derives a target-local specs fragment from the active
compiler's own `*endfile` spec and removes only the `default-manifest.o` token.
The title manifest explicitly carries both `activeCodePage=UTF-8` and
`longPathAware=true`, preserving the behavior of both original manifests.

### Proposed upstream shape

- Add long-path awareness to the canonical PSXRecomp Windows manifest.
- When GNU's `*endfile` spec injects an existing `default-manifest.o`, suppress
  that one token for targets that already use `psxrecomp_windows_manifest()`.
- Preserve all other compiler-provided start/end files and leave MSVC and
  llvm-mingw behavior unchanged.

### Acceptance tests

- The link emits no resource-merge diagnostic.
- The final PE has exactly one type-24/ID-1 manifest.
- That manifest declares UTF-8, long-path awareness, the supported OS IDs, and
  `asInvoker`.
- The app icon remains present.

## U-005: Out-of-function transfer warnings

**Status:** Confirmed
**Reproducer:**
[synthetic PS-X EXE fixture](../tests/fixtures/out_of_function_warning_fixture.py)

The resident executable generation completed with 1,438 emitted function
bodies and seven warnings. Instruction-level review found five valid
continuations and two unreachable data regions. It found no missing callable
entry, jump table, or unsupported transfer.

| Warning owner | Warning block | Terminator | Destination(s) | Parent range | Classification |
| --- | --- | --- | --- | --- | --- |
| `func_80030008` | `0x80030014` | `j` at `0x80030018` | `0x8805CD40` | `0x80030008-0x80030020` | Data after a terminal B0(38h) BIOS thunk |
| `func_80041FF8` | `0x80042064` | `j` at `0x80042064` | `0x8004207C` | `0x80041DE8-0x80042134` | Shared continuation |
| `func_800420A8` | `0x800420A8` | `bne` at `0x800420B8` | `0x80041F3C` / `0x800420C0` | `0x80041DE8-0x80042134` | Shared loop continuation |
| `func_80043068` | `0x800430D8` | `bne` at `0x800430E0` | `0x80043058` / `0x800430E8` | `0x80042FD0-0x800431B8` | Shared loop continuation across false interior partitions |
| `func_8004A9E4` | `0x8004A9E4` | `j` at `0x8004A9E4` | `0x8825CD40` | `0x8004A9E4-0x8004A9EC` | Unreachable data between functions |
| `func_8006A3A0` | `0x8006A3A0` | `beq` at `0x8006A3A8` | `0x8006A3D0` / `0x8006A3B0` | `0x8006A3A0-0x8006A3D8` | Shared early-exit continuation |
| `func_8006A3B4` | `0x8006A3C0` | `bne` at `0x8006A3C8` | `0x8006A3B0` / `0x8006A3D0` | `0x8006A3A0-0x8006A3D8` | Shared loop continuation |

The emitter already writes a terminating CPS transfer for every branch outcome
and for the jumps. Its final function-body pass then sees no in-piece
successors and prints the warning. For a reachable continuation it appends a
next-function call after the generated `return`, making the call unreachable.
For an unreachable data block it prints `emitting fallthrough` before the
reachability check, but emits no fallthrough call. The same diagnostic
therefore describes two different outcomes.

The fixture contains only synthetic instructions. It reproduces both warning
shapes, verifies the explicit transfers and dead continuation fallback, and
proves that the data warning claims a fallback that is not emitted:

```powershell
python tests\fixtures\out_of_function_warning_fixture.py --emitter psxrecomp\recompiler\build\psxrecomp-game.exe
```

### Local action

The false interior seeds `0x80042FFC` and `0x80043068` were removed. The first
is in the register-save prologue begun at `0x80042FD0`; the second begins with
a conditional branch whose operands were loaded by the preceding block. A
scratch regeneration still produced 1,438 functions, 33 shards, the same
dispatch output, and the same seven warnings because automatic discovery
reconstructs the interior pieces.

No warning address was promoted to a new seed.

### Proposed upstream shape

1. Track whether branch/jump emission already terminates every path.
2. Do not append or report next-function fallthrough after such a terminator.
3. Print an emission claim only after the reachability decision.
4. Keep a diagnostic for a genuinely unterminated reachable block.
5. Stop a JAL-discovered packed BIOS thunk at its recognized indirect jump,
   rather than interpreting unreachable bytes up to the next function.
6. Add the synthetic branch and BIOS-tail cases as regression fixtures.

## U-006: Same-address title modules

**Status:** Title-specific

The generic play-free detector finds `FRONT.BIN` and `GAME.BIN` at the same
inferred file base, `0x80098B60`. That is consistent with mutually exclusive
front-end and gameplay modules. The existing generic detector already supports
the discovery mechanism; the missing work is a verified G-Police profile,
loader checks, and static roots.

Keep this title-local unless implementing the profile exposes a generic
framework limitation.

## U-007: Negative existence checks in setup-package audit

**Status:** Confirmed
**Local workaround:** The generated dispatch path is assembled from
`GPOLICE_GENERATED_STEM` in [the title CMake file](../CMakeLists.txt).

### Observation

The setup-host packager checks every literal
`${CMAKE_CURRENT_SOURCE_DIR}/...` reference and rejects paths absent from the
staged tree. It recognizes paths inside `if(EXISTS ...)` as optional, but not
paths inside `if(NOT EXISTS ...)`.

The title uses a negative existence probe to enable the clean setup-host path
when its generated dispatch file is absent. Generated game code must not be
shipped in the owned-input setup package, so the packager removes it and then
incorrectly reports the probe target as a missing source dependency.

### Proposed upstream shape

- Treat literal paths used by both positive and negative `EXISTS` predicates as
  optional probes; or
- explicitly exclude configured generated-output markers from the staged
  source-input audit.

A regression fixture should prove that a missing path used only by
`if(NOT EXISTS ...)` passes while an unguarded missing source still fails.

## Filing checklist

Before opening an upstream issue or pull request:

1. reproduce against an unmodified current upstream checkout;
2. reduce the case to synthetic or redistributable fixtures;
3. record host OS, compiler, generator, and exact commits;
4. state expected and actual behavior;
5. link the local workaround without requiring upstream to adopt title policy;
6. add a regression test that fails before the proposed change;
7. update this document with the issue or pull-request URL and final status.
