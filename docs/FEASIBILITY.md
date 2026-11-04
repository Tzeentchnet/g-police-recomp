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
5. provides a foundation for overlay and data-format research.

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
| Clean setup-host configure/build | Pass | Configures without pre-existing generated game or BIOS code |
| Clean full-runtime configure/build | Pass | Generated game dispatch and SCPH5552 backend required |
| Setup-host self-check | Pass | Setup host reports the expected executable identity and mode |
| Full-runtime self-check | Pass | Game dispatch, SCPH5552 backend, and overlay-cache configuration present |
| Disc 1 bounded startup | Pass | Disc identified as `SLUS-00544`; runtime remained active for 15 seconds |
| Disc 2 bounded startup | Pass | Disc identified as `SLUS-00556`; runtime remained active for 10 seconds |
| Focused title-adapter tests | Pass | Four tests cover BIOS profile selection and setup/package wiring |
| Interactive gameplay | Not run | No mission completion or control/rendering acceptance pass |
| FMV and XA playback | Not run | Disc inventory exists, but playback has not been accepted |
| Save/load and memory card | Not run | Runtime path exists; title behavior is unverified |
| Disc change | Not run | Both discs start independently; in-game swap flow is unverified |
| Overlay native coverage | Partial | Cache enabled; `FRONT.BIN` and `GAME.BIN` discovered, not yet shipped as audited native shards |
| Setup ZIP acceptance | Not run | Source and setup host build; final archive workflow still needs acceptance |
| Linux gameplay | Not run | No current native title acceptance |
| macOS gameplay | Not run | No current native title acceptance |

## What the startup checks prove

The bounded checks prove that the full runtime can:

- load the required retail BIOS backend;
- begin execution from the PlayStation reset vector;
- identify and open either configured disc;
- reach guest execution without immediately exiting or tripping self-checks.

They do **not** prove correct rendering, audio, input, timing, mission scripting,
disc changes, save compatibility, or game completion.

## Known technical risks

### Runtime-loaded code

The resident executable is not the whole game. `FRONT.BIN` and `GAME.BIN`
contain code loaded over the same RAM region after the resident image. Until
their loader contract and entries are audited and compiled, uncovered paths
use the framework's dirty-RAM interpreter and optional local overlay cache. See
[ARCHITECTURE.md](ARCHITECTURE.md).

### Media geometry

Both supplied CUEs describe one `MODE2/2352` data track. Their committed
identities match, but they do not establish a general policy for alternate
dumps, subchannel data, or multi-track releases.

### Release packaging

The inherited setup-host model generates retail-derived code on the user's
machine and keeps it ignored. Current PSXRecomp release guidance favors bundled
generated outputs for some projects. This project has not yet selected a final
distribution model.

### Toolchain diagnostics

MinGW links currently print a non-fatal
`.rsrc merge failure: multiple non-default manifests` diagnostic. The
executable links, self-checks, and starts, but the warning needs an isolated
reproduction before release. It is tracked in [UPSTREAM.md](UPSTREAM.md).

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

No quality graduation or complete-game claim should be made before those gates
are recorded here.
