# Working with submissions

A submission is a directory, not a registered name. Keep as many attempts as you
like side by side. Each has its own `submission.yaml`, top Magic file, optional
child cells, and generated reports.

```sh
uv run bandgap new submissions/attempt-01 --track provided
uv run bandgap new submissions/attempt-02 --track custom
uv run bandgap magic -s submissions/attempt-01
uv run bandgap drc --submission submissions/attempt-01
uv run bandgap lvs -s submissions/attempt-02
```

`new` refuses to overwrite an existing directory. Both tracks receive eleven
required pin labels/ports, track metadata, and a run-directory ignore rule.
The pins are labels on empty space, not fabricated electrical terminals; move
them onto real routing as you complete the design.

The **provided** starter contains 125 unwired electrical instances, grouped by
type on a grid, with internal library geometry intact. It includes ordinary
transistor tiles, all prescribed filler devices, capacitors, resistors and bipolar
primitives. `inventory.csv` maps their names to schematic paths. A separate
`tap_palette.mag` offers one sample of each tap type; it is not part of the
circuit and does not prescribe a tap count. Place the parts, add appropriate
taps and substrate contacts, and route the schematic. The tray passes initial
DRC with the bundled PDK but intentionally fails circuit LVS.
See the [starter instructions](../templates/provided/README.md) and
[design/validation record](starter-design.md).

The **custom** starter remains a pin-only canvas with no device instances or
geometry. It fails physical checks with “no physical geometry” until you begin
drawing; later LVS still requires the whole schematic. A blank canvas is never
accepted merely because Magic reports zero DRC errors.

## Tracks preserve the same circuit

- **Provided:** place and connect the supplied immutable tiles. The direct Magic
  startup configuration adds `cells/REY_ATR_SKY130A` to the search path.
- **Custom:** draw your own device layouts. Use new names for custom tiles;
  the supplied tile names are reserved. Device models, effective dimensions and
  connections must still match the fixed schematic.

Changing placement, orientation, fingers, diffusion sharing, contacts and routing
is allowed within the selected track's rules. Splitting a transistor into parallel
fingers with the same model, length and total width can pass LVS. Changing width
and length while merely preserving W/L does not. Neither track allows circuit
redesign based on similar measured behavior. The acceptance suite tests this
LVS distinction explicitly; a real finger implementation must also pass DRC.

All libraries in the bundled Sky130A installation remain available. Library
availability is not permission to change the circuit: added or substituted
standard cells must still match the fixed schematic under LVS.

## Choose the active directory

Selection order is:

1. Explicit `--submission DIRECTORY` or `--reference` (mutually exclusive).
2. `default_submission` in this checkout's ignored `tools.local.yaml`.
3. The reference, when neither is specified.

```yaml
# tools.local.yaml — relative paths are relative to this checkout
default_submission: submissions/attempt-01
```

With that setting, `uv run bandgap drc` works on attempt-01. Use
`uv run bandgap drc --reference` to override it. The CLI prints the selected
absolute directory, track, PDK and output directory on every evaluation invocation.
`bandgap env` deliberately emits only shell exports, and `pdk compare` emits JSON.

## Isolated results

Submission reports default to `DIRECTORY/runs/MODE/PROFILE`. Reference reports
use `runs/reference/MODE/PROFILE` in the checkout. Therefore two entries, C/RC
experiments and typical/corner profiles do not overwrite each other's reports.
`--out DIRECTORY` overrides this if you need another experiment workspace.

Run dependent checks with the same selection, mode, profile and output directory:

```sh
uv run bandgap extract -s submissions/attempt-01
uv run bandgap simulate -s submissions/attempt-01 --view layout --analysis dc
uv run bandgap all -s submissions/attempt-01 --profile corners
```

A partial simulation replaces that view/profile report and cannot satisfy full
scoring. Input/artifact hashes reject stale results. The official schematic is
shared across entries, but simulation reports remain isolated for reproducibility.

The reference is a demonstration and flow-validation baseline, selectable with
`--reference`; the documented starting point for participants is `bandgap new`.
Use `bandgap magic -s DIRECTORY` to edit an entry or `bandgap magic --reference`
to inspect the reference. See the [launcher guide](cli.md#open-a-layout-in-magic)
and [direct tool use](pdk.md#using-tools-directly).
