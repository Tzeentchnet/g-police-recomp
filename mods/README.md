# Title mods

No G-Police-specific runtime mod is currently shipped.

PSXRecomp still supplies its public built-in mod catalog, which is staged by
the shared packaging path. Future title mods belong here only when they are:

- optional and clearly identified;
- implemented without embedding retail game data;
- versioned and tested against the pinned framework and title executable;
- documented with any function, address, or data-format assumptions.

Reverse-engineering notes do not belong in mod manifests. Record code and
memory findings in [the architecture notes](../docs/ARCHITECTURE.md), data
structures in [the format notes](../docs/FORMATS.md), and reusable framework
gaps in [the upstream findings](../docs/UPSTREAM.md).

The companion Blender add-on is a separate tooling surface. Import/export
support should consume documented formats rather than depending on a runtime
mod or generated recompilation code.
