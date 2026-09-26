# CLI guide

Run commands from the checkout with `uv run bandgap`. uv uses the checked-in
`pyproject.toml` and `uv.lock`; no manual activation or pip commands are needed.
The Typer adapter delegates to the readable evaluator scripts and preserves
their exit codes and JSON reports.

```sh
uv run bandgap --help
uv run bandgap help
uv run bandgap help extract
uv run bandgap simulate --help
```

| Command | Purpose | Prerequisites |
| --- | --- | --- |
| `new DIRECTORY --track provided` | Create an unwired parts tray (`custom` creates a pin-only canvas) | A new directory |
| `magic [FILE_OR_DIRECTORY]` | Open a layout in Magic with project libraries | Magic and PDK; desktop display |
| `env` | Shell exports for direct EDA tools | None |
| `pdk path/install/compare` | Inspect or copy the complete bundle | No network required |
| `doctor` | Tools, hierarchy and real PDK model smoke check | Configured EDA tools and PDK |
| `drc` | Full Magic DRC, zero violations required | Layout and complete child hierarchy |
| `lvs` | Fresh connectivity extraction and schematic comparison | Layout |
| `area` | Physical paint bounding area | Layout |
| `extract` | RC or C-only export and contracted connectivity LVS | Layout |
| `simulate --view schematic` | Baseline DC, startup and stability | Canonical schematic |
| `simulate --view layout` | Extracted DC, startup and stability | Passing `extract` report |
| `score` | Validate reports, apply gates and rank | Every physical check and complete paired simulations |
| `all` | Run the full sequence | Configured tools and PDK |
| `netlist` | Regenerate both canonical schematic views into a scratch directory | Xschem and PDK_ROOT |
| `acceptance` | Run 18 positive/negative physical and report checks | Configured tools and PDK |

The checks share `--submission DIRECTORY` (or `--reference`), `--out`, `--pdk-root`, and
`--mode rc|c`. `--profile typical|corners` applies to simulations and scoring;
`--view schematic|layout` selects the view for `simulate`. Shared options that
are irrelevant to a particular physical check have no effect. `all` always
simulates both views. The default profile is typical and the default mode is RC. The track comes
from submission.yaml. Without explicit selection, local default_submission is
used, falling back to the reference. See [submissions](submissions.md).

## Open a layout in Magic

```sh
uv run bandgap magic --reference
uv run bandgap magic -s submissions/attempt-01
uv run bandgap magic templates/provided
uv run bandgap magic submissions/attempt-01/LELOTEMP_BIAS_IBP.mag
uv run bandgap magic
uv run bandgap magic --reference --dry-run
```

With no target, `magic` uses `default_submission`, falling back to the reference,
just like evaluation commands. Choose exactly one of a positional path,
`--submission`/`-s`, or `--reference`. A positional directory with
`submission.yaml` uses its declared layout; a directory without metadata opens
`LELOTEMP_BIAS_IBP.mag` directly. `templates/provided` is the shipped parts tray;
open `templates/provided/tap_palette.mag` by file path to inspect the tap samples.

The launcher uses `tools.magic` from local configuration, or `magic` on PATH;
`--magic /path/to/magic` overrides it. `--pdk-root` uses the usual PDK selection
rules. It loads the project's `magicrc`, uses full `mag` library views, and starts
in the top file's directory so sibling cells and relative references resolve.
After loading, it expands the subcells to show their colored layers, clears the
selection, and fits the whole design in the window. This changes only the display;
it does not flatten, edit or save the layout. Existing entries and the reference
get the same initial view as new submissions.
Paths containing spaces are supported. `--dry-run` prints a shell-quoted command
and working directory without opening the editor.

The layout and PDK startup file must exist. Blank and unfinished layouts can be
opened; launching does not require passing DRC or LVS. Run those checks separately
to validate hierarchy, track rules and electrical correctness. Magic opens the
selected file for editing, including when it is the reference; save edits only
where intended. The CLI waits until Magic exits and returns its exit status.

## Fast experiments

```sh
uv run bandgap extract --reference --mode c --out runs/fast
uv run bandgap simulate --reference --mode c --view layout --analysis dc --out runs/fast
uv run bandgap simulate --reference --view schematic --analysis tran --analysis stability --out runs/experiment
```

Partial analyses and C-only results are useful while iterating, but do not
qualify for official scoring. A later simulation replaces the selected
view/profile report in that output directory. Keep different experiments in
different `--out` directories.

## Schematic experiments and evaluator checks

```sh
uv run bandgap netlist --pdk-root /path/to/pdk --xschem /path/to/xschem
uv run bandgap acceptance
uv run bandgap acceptance --keep
```

Netlisting writes to `runs/netlist` by default. It never replaces the fixed
competition schematic; use a copied bench to experiment with regenerated views.
For raw report locations, measurement details and the formula, see the
[evaluation contract](evaluation.md) and [testbench guide](../testbenches/README.md).
