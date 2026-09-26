# Sky130 bandgap layout competition

Lay out the supplied `LELOTEMP_BIAS_IBP` schematic. Preserve its proportional-to-
temperature current outputs and complementary-to-temperature voltage while
reducing area and limiting the effects of wiring parasitics. The schematic,
reusable device cells, reference Magic layout, and evaluator are included here.

This is a standalone repository. uv manages Python, Typer and PyYAML; evaluation uses
Magic, Netgen, ngspice, and the **bundled full Sky130A installation**. There are no CIC tools,
parent repository scripts, network downloads, or source-repository symlinks in
the evaluation path. Xschem is useful for editing/regenerating the supplied
schematic but is not needed to evaluate a layout.

Read the [published documentation](https://habemus-papadum.github.io/lelo_bandgap_layout_competition/),
start with the [first-run guide](docs/getting-started.md), or explore the
[CLI guide](docs/cli.md). Detailed evidence and the work history are preserved
in the documentation navigation.

## Start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and clone this repository.
uv manages the pinned Python environment and locked dependencies:

```sh
git clone https://github.com/habemus-papadum/lelo_bandgap_layout_competition.git
cd lelo_bandgap_layout_competition
uv sync --locked
cp tools.local.example.yaml tools.local.yaml
# Optional: edit tool paths or default_submission in tools.local.yaml.
uv run bandgap help
uv run bandgap help simulate
uv run bandgap doctor --reference
uv run bandgap all --reference --profile typical
```

No separate PDK download is needed. The full installed Sky130A tree and support
scripts are included directly in Git. See [PDK setup and direct tool use](docs/pdk.md)
for overrides, optional cache installation, size and provenance.
`tools.local.yaml`, `submissions/` and generated `runs/` are ignored by Git.

Without a selection or local default, the input is the reference layout.
Use `--reference` explicitly for baseline checks, or `--submission DIRECTORY`
for an entry; each invocation prints its selection. A complete typical run checks DRC,
LVS, area, distributed RC extraction, both circuit views, and a development
score. The official profile is selected explicitly:

```sh
uv run bandgap all --reference --profile corners --out runs/qualification
```

This runs 45 conditions per view: five model-library sections (`tt`, `ss`,
`ff`, `sf`, `fs`), -40/27/125 C, and 1.7/1.8/1.9 V. It is a stated finite
grid, not an exhaustive sweep or Monte Carlo analysis. The model-library
sections retain typical passive corners; see [evaluation rules](docs/evaluation.md).

## Individual checks

Every command retains a readable log and a JSON result with elapsed time.
Commands return nonzero on a failed check. For a created submission, run:

```sh
uv run bandgap doctor -s submissions/attempt-01
uv run bandgap drc -s submissions/attempt-01
uv run bandgap lvs -s submissions/attempt-01
uv run bandgap area -s submissions/attempt-01
uv run bandgap extract -s submissions/attempt-01
uv run bandgap simulate -s submissions/attempt-01 --view schematic
uv run bandgap simulate -s submissions/attempt-01 --view layout
uv run bandgap score -s submissions/attempt-01
```

Simulation can be narrowed to `--analysis dc`, `--analysis tran`, or
`--analysis stability` (repeat the option to select several). Full scoring
requires all three analyses in both views. `--mode c` enables capacitance-only
development checks; distributed `--mode rc` is the default and is required for
official scoring. Use different `--out` directories for different modes or
entries. The evaluator rejects stale or altered prerequisite outputs.

The implementation is deliberately exposed: [physical checks](tools/physical.py),
[Magic commands](tools/physical.tcl), [simulation and measurement](tools/simulation.py),
and [orchestration/scoring](tools/check.py). You may copy and adapt these for
local debugging; the official rules use the published configuration and code.

## Make an entry

There are separate rankings for two tracks:

- **Provided cells:** use the supplied immutable device/passive/tap tiles and
  arrange/connect them with your own routing and assembly hierarchy. Default
  creation option: `bandgap new DIRECTORY --track provided`.
- **Custom devices:** implement the same electrical schematic with your own
  geometry or tile variants. Create with `bandgap new DIRECTORY --track custom`. PDK primitives remain
  available, but the supplied REY layout tiles are not entry components in
  this track. Give custom variants new cell names and filenames; supplied
  tile names remain reserved even if their geometry changes.
  Originality beyond named-cell reuse is a competition rule, not
  something DRC/LVS can prove.

Device types, dimensions, connectivity, and the explicit dummy devices belong
to the fixed schematic. This is a layout competition, not a circuit-sizing
competition. Consult the [cell catalog](docs/cells.md), especially the
diode-connected `D` variants and physical-only taps.

Create independent entries:

```sh
uv run bandgap new submissions/attempt-01 --track provided
uv run bandgap new submissions/attempt-02 --track custom
uv run bandgap magic -s submissions/attempt-01
uv run bandgap drc -s submissions/attempt-01
```

Provided-track entries start with 125 unwired electrical parts grouped by type,
plus a separate tap palette and an inventory mapping back to the schematic.
Placement, taps and routing remain your work; full LVS intentionally fails.
Custom-track entries retain the pin-only canvas. Both have eleven unattached
port placeholders. Preview the provided starter with
`uv run bandgap magic templates/provided` and read its
[instructions](templates/provided/README.md). Set `default_submission`
in local YAML to select your current entry; use `--reference` for baseline runs.
See [submissions](docs/submissions.md) for track rules, selection and isolated reports.

Submit `LELOTEMP_BIAS_IBP.mag` and any local child `.mag` files, with their
relative paths intact. A flat file is accepted in the custom track. All
non-PDK dependencies must be inside the entry's top-file directory or this
project. Keep the required eleven ports; arbitrary internal instance/net names
are allowed. The evaluator measures painted geometry, not an editable boundary
property, and checks complete hierarchy loading before accepting DRC/LVS.

## Circuit and experiments

- [Circuit/interface explanation](docs/design.md)
- [Editable schematic](schematic/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.sch)
- [Canonical simulation netlist](schematic/bandgap.spice) and [LVS netlist](schematic/bandgap.lvs.spice)
- [Testbench instructions](testbenches/README.md): generated decks are ordinary
  ngspice files you can copy, edit and run directly.
- [Evaluation rules, scoring and coverage](docs/evaluation.md)
- [Reference measurements and timings](docs/reference-results.md)
- [RC extraction investigation and limitations](docs/rc-validation.md)
- [Packaging/provenance](docs/packaging.md), [attribution](LICENSES/ATTRIBUTION.md),
  and [work journal](docs/journal.md)

To edit the schematic or reproduce its canonical netlists:

```sh
eval "$(uv run bandgap env)"
xschem --rcfile schematic/xschemrc schematic/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.sch
uv run bandgap netlist --output-dir runs/netlist
```

The `env` command exports the same resolved PDK root for direct tools. Regeneration writes to `runs/netlist`; it does not
replace the fixed canonical SPICE files used for judging. To experiment with
schematic changes, use a copied bench with the regenerated netlist.
