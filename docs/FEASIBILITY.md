# Feasibility and validation

This document records what the current project has demonstrated and what still
needs evidence. It replaces the inherited release-candidate framing: the
project is an active recompilation and reverse-engineering effort, not a frozen
package recipe.

Last updated: **2026-11-04**

## Scope

The current milestone is a reproducible Windows development build that:

1. accepts legally owned USA disc images and an SCPH5552-compatible BIOS;
2. generates resident game and BIOS code with the pinned PSXRecomp;
3. starts with either game disc;
4. preserves a first-run setup-host route for users without generated code; and
5. regenerates guarded native coverage for the two runtime modules from the
   user's owned disc.

The exact framework and launcher revisions are recorded in
[the project manifest](../project-manifest.toml) and
[the framework pin list](../framework_pins.txt).

## Validation matrix

| Surface | Status | Evidence |
| --- | --- | --- |
| Framework submodules | Pass | PSXRecomp `060ef0ab`; recomp-ui `dd47b18`; nested pins recorded |
| Disc 1 identity | Pass | `SLUS-00544`; size, hashes, and fingerprint match committed metadata |
| Disc 2 identity | Pass | `SLUS-00556`; size, hashes, and fingerprint match committed metadata |
| Boot executable parity | Pass | Both discs contain byte-identical 479,232-byte executables |
| Required BIOS identity | Pass | 524,288-byte SCPH5552-compatible dump matched the configured SHA-256 |
| BIOS generation | Pass | SCPH5552 backend generated through the title adapter |
| Resident game generation | Pass | 33 C shards generated; 1,438 emitted function bodies |
| Resident transfer warning audit | Pass | Seven warnings classified as five shared continuations and two unreachable data regions; no callable seed missing |
| Module loader audit | Pass | Exact destination, byte lengths, repeat-read XOR validation, copy, cache flush, and resident handoffs verified |
| Original-disc AOT profile | Pass | Either USA disc yields two hash-pinned, strict-range recipes; all guard bytes match known inputs |
| Static module build | Pass | `FRONT.BIN` and `GAME.BIN` produce two module units plus a dispatcher with 19,801 audited variants |
| Clean setup-host configure/build | Pass | Configures without pre-existing generated game or BIOS code |
| Clean full-runtime configure/build | Pass | Generated game dispatch, SCPH5552 backend, and all three static-overlay units linked |
| Windows PE resources | Pass | Setup and full builds contain one UTF-8/long-path ID-1 manifest and the application icon |
| Setup-host self-check | Pass | Setup host reports the expected executable identity and mode |
| Full-runtime self-check | Pass | Game dispatch, SCPH5552 backend, and overlay-cache configuration present |
| Disc 1 bounded startup | Pass | Disc identified as `SLUS-00544`; runtime remained active for 15 seconds |
| Disc 2 bounded startup | Pass | Disc identified as `SLUS-00556`; runtime remained active for 10 seconds |
| Full-runtime launcher | Pass | Verified Disc 1, BIOS, OpenGL settings, controller mapping, both empty card slots, and Play handoff to the runtime |
| Focused project tests | Pass | Twelve tests cover BIOS selection, overlay metadata/wiring, packaging, manifests, and warning fixtures |
| Front-module native dispatch | Pass | Headless Disc 1 run hit `0x8009DAE8`; guarded static dispatcher recorded more than ten million module-range hits |
| Game-module native dispatch | Pass | Normal Disc 1 campaign flow reached `0x800B2A60` and sustained guarded static dispatch in live mission gameplay |
| Interactive gameplay | Partial | Normal controller input covered menus, training briefing/loadout/live flight, and campaign briefing/loadout/live mission rendering; no objective or mission completion was attempted |
| FMV and XA playback | Pass | Campaign STR/MDEC video, briefing XA, and nonzero host SPU and CD/XA samples were observed; startup underruns and long-run ring drops still need tuning |
| Save/load and memory card | Partial | Runtime created valid 128 KiB cards and the launcher reported both as 0/15 blocks; no title save was created, loaded, or restart-tested |
| Disc change | Not run | Both discs start independently; in-game swap flow is unverified |
| Overlay native coverage | Partial | Both known modules have audited static shards and live native evidence; indirect-entry completeness remains unproven |
| Setup ZIP acceptance | Pass | Windows `0.1.1` archive passed payload, platform-copy, native-emitter, and clean extracted-source rebuild checks |
| Linux gameplay | Not run | No current native title acceptance |
| macOS gameplay | Not run | No current native title acceptance |

## What the startup checks prove

The bounded checks prove that the full runtime can:

- load the required retail BIOS backend;
- begin execution from the PlayStation reset vector;
- identify and open either configured disc;
- reach guest execution without immediately exiting or tripping self-checks.

The separate Disc 1 interactive smoke provides bounded rendering, input,
launcher, media, and live gameplay evidence. Neither test proves complete
timing or mission scripting, objective completion, disc changes, save
compatibility, or game completion.

## Known technical risks

### Runtime-loaded code

The resident executable is not the whole game. `FRONT.BIN` and `GAME.BIN`
contain code loaded over the same RAM region after the resident image. Their
loader contract is verified and both have hash-pinned guarded static shards,
but the AOT audit intentionally does not claim complete indirect-entry
coverage. Unknown PCs or changed bytes still fall back to the framework's
dirty-RAM interpreter and optional local overlay cache. `FRONT.BIN` has live
native evidence, and the Disc 1 interactive smoke reached live `GAME.BIN`
native dispatch. Complete indirect-entry coverage remains unproven. See
[ARCHITECTURE.md](ARCHITECTURE.md).

### Media geometry

Both supplied CUEs describe one `MODE2/2352` data track. Their committed
identities match, but they do not establish a general policy for alternate
dumps, subchannel data, or multi-track releases.

### Release packaging

The inherited setup-host model generates retail-derived code on the user's
machine and keeps it ignored. Current PSXRecomp release guidance favors bundled
generated outputs for some projects. The Windows owned-input setup ZIP now
passes the local package gates and rebuilds its setup host from the extracted
archive, but this project has not yet selected a final public distribution
model.

### Windows toolchain compatibility

WinLibs GCC 16.2 injects a long-path `default-manifest.o` even when the target
already supplies the PSXRecomp UTF-8 manifest. The title now preserves both
settings in one manifest and removes only that injected end-file token through
a target-local GNU specs override. Setup-host and full-runtime links are clean,
and their PE resource trees each contain exactly one type-24/ID-1 manifest.

The override fails configuration if a future GNU toolchain exposes an
unrecognized end-file spec rather than silently restoring duplicate resources.
MSVC and llvm-mingw do not use this workaround and still need release-host
acceptance.

### Data formats

The resource container framing, texture index planes, palettes, and VAG
records now have repeatable structural evidence. Model, animation, scene, and
coordinate semantics are not yet identified. See [FORMATS.md](FORMATS.md).

## Milestone exit criteria

A gameplay-ready milestone should require at least:

- an interactive pass through menus, training, and representative missions;
- verified FMV, music, radio, and briefing playback;
- save creation, load, and restart checks;
- an in-game Disc 1 to Disc 2 transition or a documented substitute flow;
- audited coverage or acceptable fallback behavior for both code modules;
- repeatable setup-package acceptance on Windows;
- a recorded decision for Linux and macOS support;
- no unexplained linker/resource warnings in release builds.

The 2026-11-04 smoke covers the launcher, menu, training, campaign-entry, and
live mission control/rendering paths. It intentionally does not satisfy the
representative mission-completion or save-lifecycle gates.

No quality graduation or complete-game claim should be made before those gates
are recorded here.
