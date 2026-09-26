# Imported design provenance

The bandgap schematic and reference layout are by Carsten Wulff, extracted from
`wulffern/lelo_temp_sky130a` at revision
`e439fe6b9351ea47a288847131337f483b2dbfcd`. The source README names Carsten Wulff;
the schematic title blocks name Carsten Wulff / Carsten Wulff Software.

The REY_ATR device, passive, and tap tiles come from
`wulffern/rey_atr_sky130a` at revision
`3742bcc0521d36627485a0c5db2ebef7b428ed2c`. Its README credits `wulff`.

The per-file source path, original SHA256, and packaged SHA256 are recorded in
[`cells/manifest.json`](../cells/manifest.json). Source paths are provenance
identifiers, not runtime dependencies. Original geometry and electrical
connectivity are preserved. Packaging changes are described in
[`docs/packaging.md`](../docs/packaging.md).

Neither checked-out upstream repository supplied a LICENSE/COPYING file or an
explicit license notice in the imported `.mag`, `.sch`, or `.sym` files at these
revisions. This attribution file records that absence; it does not create a
license grant or assert that the designs are public domain. The local extraction
was made at the workspace owner's request. Confirm the applicable upstream
permission before distributing the imported designs as a public competition.

Sky130A device symbols, primitive geometry, technology decks, and device models
remain external prerequisites. No PDK files are copied into this package; their
installed notices and license terms continue to apply.
