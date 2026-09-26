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
| `acceptance` | Run 16 positive/negative physical and report checks | Configured tools and PDK |

The checks share `--layout`, `--out`, `--track provided|custom`, and
`--mode rc|c`. `--profile typical|corners` applies to simulations and scoring;
`--view schematic|layout` selects the view for `simulate`. Shared options that
are irrelevant to a particular physical check have no effect. `all` always
simulates both views. The default profile is typical and the default mode is RC.

## Fast experiments

```sh
uv run bandgap extract --mode c --out runs/fast
uv run bandgap simulate --mode c --view layout --analysis dc --out runs/fast
uv run bandgap simulate --view schematic --analysis tran --analysis stability --out runs/experiment
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
