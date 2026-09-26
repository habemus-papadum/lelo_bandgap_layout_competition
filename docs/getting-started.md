# Your first run

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), Magic,
Netgen, ngspice with KLU, and an installed Sky130A PDK. Xschem is optional unless
you want to view or regenerate the schematics. uv manages Python and all Python
packages; the EDA tools and PDK remain workstation prerequisites.

## Set up a checkout

```sh
git clone https://github.com/habemus-papadum/lelo_bandgap_layout_compeititon.git
cd lelo_bandgap_layout_compeititon
uv sync --locked
cp tools.local.example.yaml tools.local.yaml
```

Edit `tools.local.yaml` with your tool paths and the directory **containing**
`sky130A/`. Paths can be absolute or relative to the checkout. This file is
ignored by Git. If everything is already on PATH, exporting `PDK_ROOT` is enough.

## Discover and check

```sh
uv run bandgap help
uv run bandgap help simulate
uv run bandgap doctor
uv run bandgap all --profile typical
```

The full typical flow takes about two minutes on the measured reference machine.
DRC, LVS, area and extraction each take less than a second. See
[measured timings](reference-results.md) before choosing longer runs.

## Start laying out

Choose the [provided-cell or custom-device track](../README.md#make-an-entry).
The provided-cell starting point preserves the reference hierarchy:

```sh
mkdir -p submissions
cp -R reference/LELO_TEMP_SKY130A submissions/my_entry
uv run bandgap drc --layout submissions/my_entry/LELOTEMP_BIAS_IBP.mag --out runs/my_entry
uv run bandgap lvs --layout submissions/my_entry/LELOTEMP_BIAS_IBP.mag --out runs/my_entry
uv run bandgap all --layout submissions/my_entry/LELOTEMP_BIAS_IBP.mag --out runs/my_entry
```

Use the same layout, track, mode and output directory for dependent checks. The
CLI rejects stale reports after inputs change. Use a separate output directory
for an experiment you want to keep. Read the [rules](evaluation.md) before
optimizing the score and the [cell catalog](cells.md) before changing hierarchy.

## Qualify an entry

```sh
uv run bandgap all --profile corners --layout submissions/my_entry/LELOTEMP_BIAS_IBP.mag --out runs/my_entry-corners
```

This runs the declared 45-condition grid in both views (about 20 minutes on the
reference machine). Official-profile scoring requires RC, zero DRC errors,
matching LVS, complete simulations and the electrical eligibility gates.
