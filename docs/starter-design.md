# Starter inventory and the placement exercise

Implemented on 2026-09-26 after assessing what the starter would disclose.
The provided track now starts from a schematic-derived parts tray; the custom
track retains its pin-only canvas. The [Magic launcher](cli.md#open-a-layout-in-magic)
can open `templates/provided` or an individual submission. Each provided entry
includes the [starter instructions](../templates/provided/README.md).

## What the supplied materials already disclose

The published circuit already specifies more than total transistor sizes.
The [canonical LVS netlist](../schematic/bandgap.lvs.spice) names individual
`REYATR_*` tile instances, explicitly enumerates their multiplicities, and gives
MOS tile definitions with `nf=2`. For example, the current-source branch lists
eight `xca1` instances of `REYATR_PCH_4C5F0`; that tile's model parameters include
`W=3.2`, `L=0.94`, and `nf=2`. The [cell catalog](cells.md) publishes those same
parameters and explains internal connections. The complete reference layout is
also distributed in this repository.

Consequently, providing the schematic's electrical parts inventory would mostly
remove transcription and import work. It would not newly reveal a secret finger
count. This is a conclusion about the current competition materials, not a claim
that finger partitioning is generally an unimportant analog layout decision.

In the provided track, each supplied tile's internal geometry is immutable.
Students can arrange and connect tiles, but cannot change the fingers inside
one. Alternative electrically equivalent assemblies still have to satisfy LVS.
In the custom track, equivalent finger partitioning remains a layout choice:
the evaluator accepts electrically equivalent parallel devices while rejecting
dimension changes that merely preserve W/L. The acceptance suite includes that
comparison. The published `nf=2` implementation is an example, not a requirement
that every custom transistor reproduce its physical finger arrangement.

If discovering a decomposition without seeing the original implementation is
intended to be part of the exercise, withholding a populated starter alone
would not achieve that. The distributed schematic hierarchy, cell catalog and
reference already expose the original choices. Changing that teaching objective
would require revisiting those published inputs and the competition rules.

## What copying the physical reference would decide for students

The physical assembly hierarchy carries additional choices: device grouping,
orientation, tap locations, stack boundaries, and use of diode-connected `D`
variants. A template preserving those groups would give students part of a
placement solution. Even a scrambled inventory can encourage students to regard
the reference's tap count as the correct count for any new placement.

That is particularly misleading for taps. They provide physical well/substrate
connections; the appropriate arrangement depends on the final layout. Their
empty schematic views do not make them optional. Conversely, the explicit
rail-tied filler transistors are modeled circuit devices and cannot be omitted
as if they were decorative spacing. These distinctions are documented in the
[tile catalog](cells.md#bipolar-primitive-and-fillers).

The `D` variants short drain and gate inside the tile. The canonical schematic
uses ordinary transistor tiles and specifies such connections through nets.
Automatically choosing the reference's `D` variants would make a small physical
implementation choice for the student, even though the required electrical
connection is already public.

## Implemented boundary

The starter uses the schematic as the authority for electrical inventory.
It contains 125 instances of nine electrical tile types, including all 27 modeled
rail-tied dummy/filler transistors. Ordinary schematic tiles replace the
reference's preconnected `D` variants, leaving those connections to the student.

All electrical parts are direct top-level instances, sorted by type into rows on
a square grid. Stable instance names join schematic hierarchy components with
`__`; `inventory.csv` records the original paths. Internal library geometry is
unchanged. There are no reference placement groups, orientations, tap stacks or
inter-cell wires. Grid pitch is calculated from actual painted bounds with at
least 5 um clearance; it is not based on the smaller `FIXED_BBOX` properties.
The grid stores parts and is not a suggested analog floorplan. The eleven top
ports remain unattached labels to the left, ready to be moved onto final wiring.

`tap_palette.mag` is a separate drawing with one example of each of the ten tap
types. It is copied into each new provided entry, but is not instantiated by its
circuit top. Students choose and duplicate taps for their own placement, following
the catalog's stack/abutment guidance and connecting bulk terminals to the proper
rails. They also need to consider bipolar substrate contacts. This avoids
implying that the reference's tap count is universally sufficient.

The [generator](../starter.py) and committed assets are reproducible without EDA
tools. It deliberately supports the bundled schematic's explicit assembly
instances and rejects unsupported multiplicities/constructs. The source hash,
cell hashes, counts and painted bounds are recorded in `provenance.json`.
`bandgap new` simply copies the committed template; custom creation is unchanged.

## Validation and known initial conditions

The proposed intermediate reference-hierarchy transformation was unnecessary
once the schematic became the inventory source. Instead, positive LVS checks
validate every electrical tile type independently, including terminal identities
and device properties, against the schematic definitions. The bipolar fixture
explicitly maps the primitive's Emitter/Collector/Base ports to its schematic
model terminals. All nine types pass LVS and isolated DRC with the bundled PDK.
The original reference also passes fresh DRC and LVS.

The full tray passes DRC with zero violations. Its flattened extraction contains
228 primitive devices: 128 ordinary PFET fingers, 24 low-threshold PFET fingers,
38 NFET fingers, 13 capacitors, 16 resistors and nine bipolar devices. These agree
with the independently counted schematic inventory. Full circuit LVS reports
non-equivalence, as expected from disconnected parts and unattached top ports.
This is not accepted as a finished competition entry, and successful initial
DRC does not prove sufficient well/substrate contacts or connected supplies.

Magic reports three `device missing 2 terminals` warnings for each resistor
tile: its immutable geometry contains three uncontacted poly strips alongside
the two contacted resistors. The same three warnings occur in reference
extraction. Flattening eight tile instances gives 24 warnings. Validation checks
every feedback box against those specific strip coordinates; the 16 intended
resistors extract and each resistor tile passes LVS. These are inherited tile
features, not missing starter devices. Do not treat unrelated extraction warnings
in a completed submission as covered by this explanation.

Extraction also models shared substrate connectivity despite the spacing between
cells. That does not replace drawn substrate contacts or proper rail routing.
The `.mag` files have reproducible zero timestamps; Magic's initial timestamp
messages are expected. Cells are resolved through the project's library paths,
and the launcher uses a filename relative to its working directory to avoid
spurious inferred-sibling-path warnings.

Fourteen tool-free tests check creation, reproducibility, known counts and filler
instances, unique names, complete hierarchy, and pairwise painted clearance.
[Real-tool validation](../tests/starter_acceptance.py) retains per-cell DRC/LVS,
reference checks, full-tray checks and direct Magic loading/extraction feedback
under `runs/starter-validation-*`. These tests qualify the starter with the
bundled PDK; no circuit simulations are claimed for an unconnected tray.
