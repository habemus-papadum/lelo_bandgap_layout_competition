# Your first run

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Magic,
Netgen and ngspice with KLU. Xschem is optional for schematic editing. The full
measured Sky130A installation is already bundled in this repository.

```sh
git clone https://github.com/habemus-papadum/lelo_bandgap_layout_competition.git
cd lelo_bandgap_layout_competition
uv sync --locked
uv run bandgap help
uv run bandgap doctor --reference
```

If tools are not on PATH, copy `tools.local.example.yaml` to `tools.local.yaml`
and set their executable paths. No PDK installation is needed. See
[PDK configuration](pdk.md) if your environment already exports `PDK_ROOT`.

## Create your own entry

```sh
uv run bandgap new submissions/attempt-01 --track provided
uv run bandgap new submissions/attempt-02 --track custom
uv run bandgap drc --submission submissions/attempt-01
```

The initial DRC invocation intentionally fails: the generated layout contains
pin labels but no geometry. Start drawing with Magic; no reference layout is
copied into an entry. Read the [submission guide](submissions.md),
[cell catalog](cells.md), and [fixed-schematic rules](evaluation.md).

```sh
eval "$(uv run bandgap env)"
magic -rcfile "$BANDGAP_ROOT/magicrc" submissions/attempt-01/LELOTEMP_BIAS_IBP.mag
```

## Check and qualify

```sh
uv run bandgap drc -s submissions/attempt-01
uv run bandgap lvs -s submissions/attempt-01
uv run bandgap all -s submissions/attempt-01 --profile typical
uv run bandgap all -s submissions/attempt-01 --profile corners
```

Every evaluation prints its selected directory and isolates reports by entry,
mode and profile. Set `default_submission: submissions/attempt-01` in local YAML
to omit `-s` for your current work. `--reference` always selects the demonstration
baseline instead:

```sh
uv run bandgap all --reference --profile typical
```

On the reference machine the typical flow takes about two minutes and the
45-condition grid in both views takes about twenty minutes. Physical checks are
much quicker. Consult the [measured timings](reference-results.md) and
[CLI guide](cli.md) for independent checks and partial analyses.
