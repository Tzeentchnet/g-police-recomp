# Title mods

The title catalog provides three launcher Quick Mods:

- `psx.enhancement.pgxp` places PGXP Precision in the launcher's Quick Mods
  card. The runtime still uses the framework-owned `psx.pgxp` plugin.
- `psx.enhancement.fast-loading` exposes a fixed 4x Fast Loading Quick Mod
  through the framework-owned `psx.fast-loading` plugin. It accelerates host
  pacing only while G-Police's non-FMV loading predicate is active; guest CD
  deadlines, interrupts, callbacks and frame progression remain authoritative.
- `psx.enhancement.draw-distance` uses a title-owned guarded plugin to select
  a stress-tested 145,000-unit extended distance without forcing the frontend's
  coupled frame-rate reduction.

Fast Loading and PGXP Precision are enabled by default for fresh launcher
profiles; Extended Draw Distance remains opt-in. Existing saved mod choices
continue to override these defaults. The 4x loading mode was validated through
boot, frontend handoffs, the `FRONT.BIN` to `GAME.BIN` campaign transition,
live mission entry, XA/FMV playback, shared savestates and mission restart.
Major loading windows completed about 3.8-3.9x faster with matching guest-frame
boundaries and sector totals. The title override intentionally does not expose
the framework package's unvalidated adjustable or uncapped modes.

Run `launch.bat` and use the dashboard's **Quick Mods** card to enable these
features before starting the game. The same switches are available on the
launcher's **Mods** page. Quick Mods is shown before a compact two-slot memory
card section so the enhancement controls are visible without searching through
the normal Settings page. Changes take effect on the next game launch.

The draw-distance feature raises the normal 110,000-unit distance by 31.8% to
a fixed 145,000 units, 11.5% beyond the native option table's 130,000-unit
maximum. It is fixed rather than adjustable because farther values create
materially higher geometry and GPU packet pressure. A sustained 145,000-unit
stress run used up to 53,264 of the 61,440-byte packet arena, leaving 8,176
bytes of headroom, with no dropped or cancelled GPU DMA walks and no watchdog
freeze events. On the same route, the native 130,000-unit setting peaked at
39,196 bytes, leaving 22,244 bytes of packet-arena headroom. Packet peaks varied
between otherwise matched runs, so these figures are validation margins rather
than a linear performance comparison with the stock distance. A 160,000-unit
run produced a substantial additional workload and is not shipped. Extended
draw distance can reduce performance in busy scenes and uses isolated savestate
slots because it changes guest-visible culling and workload.

PSXRecomp still supplies its public built-in mod catalog, which is staged by
the shared packaging path. The title catalog is staged from `preloaded/` after
the framework catalog so deliberate same-ID overrides are explicit. Future
title mods belong here only when they are:

- optional and clearly identified;
- implemented without embedding retail game data;
- versioned and tested against the pinned framework and title executable;
- documented with any function, address, or data-format assumptions.

Reverse-engineering notes do not belong in mod manifests. Record code and
memory findings in [the architecture notes](../docs/ARCHITECTURE.md), data
structures in [the format notes](../docs/FORMATS.md), and reusable framework
gaps in [the upstream findings](../docs/UPSTREAM.md).

The companion
[G-Police Blender](https://github.com/Tzeentchnet/G-Police-Blender) add-on is a
separate tooling surface. Import/export support should consume documented
formats rather than depending on a runtime mod or generated recompilation code.
