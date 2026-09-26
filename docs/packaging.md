# Standalone packaging record

This records the initial extraction. The later [bundled PDK](pdk.md) supersedes
references below to an external PDK prerequisite.

2026-09-26. This records the extraction work authorized after restoring REY_TR
and verifying representative original full-sensor checks. Work used the source
files read-only; temporary generation and physical checks ran outside the source
IP. No CIC generator, Makefile, netlisting wrapper, or source-repository link is
needed by the packaged assets.

## Imported closure and transformations

1. Recursively followed `use` statements from `LELOTEMP_BIAS_IBP.mag`. Copied
   exactly 45 local Magic files: 22 LELO circuit/assembly cells and 23 REY_ATR
   reusable tiles. The PDK bipolar primitive remains external. REY_TR is not in
   this bandgap closure; its missing antenna cell belonged to the full sensor.
2. Copied the corresponding REY_ATR schematic and symbol views, and recursively
   followed the bandgap's schematic subcircuits. This added the three logical
   LELO cells (`LELOTEMP_BIAS_IBP`, `LELOTEMP_OTAR`, `LELOTEMP_BIPOLAR`). Total:
   45 Magic, 26 schematic, 26 symbol files; 97 imported view files.
3. Kept tile views together in `cells/REY_ATR_SKY130A`; put logical circuit
   views in `schematic/LELO_TEMP_SKY130A` and physical assemblies in
   `reference/LELO_TEMP_SKY130A`. Original cell names, geometry, labels,
   parameters, explicit rail-tied dummy/filler devices, and hierarchy survive.
4. Rewrote only Magic `use` directory references: local paths are relative to
   the containing cell; the PDK cell uses
   `$PDK_ROOT/sky130A/libs.ref/sky130_fd_pr/mag`. The upstream `$PDKPATH` variable
   would have added an undocumented environment dependency.
5. Removed three decorative `cborder/border_xs.sym` title-block instances from
   the three circuit schematics. This avoids a cpdk dependency without changing
   electrical connectivity. Author credit is retained in `LICENSES/ATTRIBUTION.md`.
6. Added a project Xschem configuration with explicit package and installed PDK
   paths. It resets global/user library search paths, uses angle-bracket bus
   names, and enables `top_is_subckt`.
7. Generated `schematic/bandgap.spice` with full PDK simulation parameters, and
   `schematic/bandgap.lvs.spice` using Xschem's `lvs_netlist=1` view. Both contain
   the complete pure schematic hierarchy with exactly one OTA definition.
   Source bench inclusion of `LELOTEMP_OTAR_lpe.spi` is not carried over.
8. Removed generated absolute source-path comments and the final `.end`, making
   the netlists relocatable subcircuit libraries. Generated `cells/tiles.spice`
   separately for standalone participant tile experiments. Recorded all original
   and packaged imported-file SHA256s, source revisions, and immutable tile
   hashes in `cells/manifest.json`.

The LVS view omits simulation diffusion-area/perimeter formulas, as the installed
PDK symbols specify for LVS. This explains the two small canonical files; they
are the same electrical circuit, not distinct design baselines. External device
model includes belong to the testbench. None of the canonical netlists references
an extracted amplifier, CIC utility, or source IP path.

## Reproduction and checks

From the competition directory:

```sh
# PDK_ROOT points to the directory containing sky130A.
uv run bandgap netlist --output-dir runs/netlist
# Inspect/edit schematics using the same explicit library configuration.
xschem --rcfile schematic/xschemrc schematic/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.sch
```

`netlist.py` uses only Python's standard library and the Xschem executable. It
keeps process diagnostics next to the generated files, requires a fresh artifact,
rejects missing symbols/errors, and checks the published top-level port order.
It accepts the known Xschem headless success codes 0 and 10 only when those
artifact checks pass. It never modifies the shipped canonical files by default.

Editing a `.sch` file alone does not change evaluation: the evaluator reads
`schematic/bandgap.spice` and `schematic/bandgap.lvs.spice`. Regenerate into
`runs/netlist` and point a copied experimental bench at that output to study
schematic changes. The published canonical files remain the fixed circuit for
competition entries; participant layout changes must match that circuit.

Fresh checks during packaging:

| Check | Result | Observed wall time |
| --- | --- | ---: |
| Regenerate both canonical views from bundled sources | Byte-identical after documented path normalization | 0.27 s in relocated copy |
| Compare canonical LVS topology with source generated CDL | Equal after removing comments and normalizing source `[]` buses to `<>` | Less than 0.1 s |
| Load entire reference hierarchy and run Magic `drc(full)` from relocated copy | All local children and external PDK bipolar read; zero errors | 0.47 s |
| Search copied circuit assets for source absolute paths / source library links | None; only documented PDK variable remains | Less than 0.1 s |

The portability spike copied only `schematic`, `cells`, and `reference` into
`/tmp/bandgap-packaging/portable`, ran Xschem from `/tmp`, and ran Magic from the
copy. Xschem's project configuration excludes aicex/global user library search
paths. The fresh netlists were byte-identical to the supplied copies. Magic used
only the relocated hierarchy and installed PDK. Its reported file-grid scale was
approximately 0.005 µm; view bounds were `-88 0 19576 21292` file units. These
bounds are a packaging observation, not the official area algorithm.

The direct Magic script loaded the reference top, expanded it, selected the full
DRC deck, waited for DRC, and counted `drc listall why` locations. All dependency
load messages were inspected. The evaluator additionally performs
independent hierarchy preflight so a missing cell cannot masquerade as zero DRC
errors. This packaging check does not qualify RC extraction or corners; those
checks are recorded separately.

Temporary scripts, raw generated views and tool logs remain in
`/tmp/bandgap-packaging/` for this working session. The project-level evaluation
logs and stable summarized results are the maintained participant interface.

## Usage and provenance notes

The tile catalog in [cells.md](cells.md) distinguishes the five diode-connected
Magic variants from their ordinary four-pin schematic symbols, physical-only
tap views, explicit filler devices, and the required PDK bipolar cell. Do not
assume that every independent `.sch` file is an independent active circuit.

No imported repository license notice was found at the recorded revisions.
[Attribution](../LICENSES/ATTRIBUTION.md) identifies the authors/source revisions
and records the permission status without inventing a grant. This does not
prevent the authorized local extraction; it remains a publication consideration.
