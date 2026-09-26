# Bundled PDK and direct tool use

A normal clone includes the **entire installed Sky130A tree**, including the HD
standard-cell library and all primitive views, plus the installation's support
scripts. Nothing was trimmed to the reference's immediate dependencies. There
are no submodules, Git LFS objects, recursive-clone steps or PDK downloads.
This is the full Sky130A installation we measured, not every optional library
that open_pdks can build. Sky130B is a different variant and is not included.

The Sky130A tree contains 4,125 files, totalling 469,372,636 bytes (about 448 MiB;
457 MiB of allocated disk space on the original machine). With support scripts,
the verified snapshot has 4,169 files. The largest file is about 71 MB. Git's
compressed transfer size is smaller than the checked-out size; the initial
PDK push transferred a 75.41 MiB Git pack.

## Default and overrides

The default is this checkout's `pdk/`. No installation is required. PDK selection
uses this precedence:

1. `--pdk-root DIRECTORY` on an evaluation/netlist/environment command.
2. Internal `BANDGAP_PDK_ROOT` set by the CLI for its child processes.
3. `pdk_root` in `tools.local.yaml`.
4. The shell's `PDK_ROOT`, if already exported.
5. The bundled `pdk/` directory.

Every root means the directory **containing `sky130A/`**. Relative local-config
paths are relative to the checkout; explicit CLI paths are also resolved by the
project's PDK resolver relative to the checkout. The selected path is printed
before evaluation. `uv run bandgap pdk path` prints the effective root.
If your shell exports an older `PDK_ROOT`, unset it to use the bundle by default.
EDA executables remain external and are found on PATH or through local YAML.

## Optional offline installation elsewhere

```sh
uv run bandgap pdk install
uv run bandgap pdk install /some/other/pdk-directory
uv run bandgap pdk compare /some/other/pdk-directory
uv run bandgap doctor --reference --pdk-root /some/other/pdk-directory
```

Without a destination, `install` uses
`${XDG_CACHE_HOME:-$HOME/.cache}/lelo_bandgap_layout_competition/pdk`.
It copies the full bundle, verifies its file hashes, and refuses an existing
path rather than modifying another installation. It does not silently change
your default configuration. Set `pdk_root` in local YAML or pass `--pdk-root`
when you want to use the copy. `compare` returns JSON with matching, changed,
missing and extra paths, and exits nonzero for differences. It compares the
Sky130A and support-script trees; unrelated variants such as Sky130B are ignored.

## Using tools directly

For Magic, `uv run bandgap magic --reference` or
`uv run bandgap magic -s submissions/attempt-01` handles executable selection,
PDK setup and library paths. See the [launcher guide](cli.md#open-a-layout-in-magic)
for raw file/directory targets and overrides. The following commands are useful
when starting tools outside the CLI.

Load shell-quoted exports for the same resolved PDK:

```sh
eval "$(uv run bandgap env)"
# Or select another installation explicitly:
eval "$(uv run bandgap env --pdk-root /some/other/pdk-directory)"
```

This sets `PDK_ROOT` and `BANDGAP_ROOT`. The commands below assume the EDA
executables are on PATH; otherwise use their absolute executable paths. Local
YAML tool paths are used by the CLI, not automatically added to your shell PATH.

```sh
magic -rcfile "$BANDGAP_ROOT/magicrc" "$BANDGAP_ROOT/submissions/attempt-01/LELOTEMP_BIAS_IBP.mag"
xschem --rcfile "$BANDGAP_ROOT/schematic/xschemrc" "$BANDGAP_ROOT/schematic/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.sch"
# Run from a generated analysis directory after copying/editing its deck:
ngspice -n -D ngbehavior=hsa -D skywaterpdk -b case.spice
```

The project's `magicrc` sources the chosen PDK's setup and adds the supplied tile
library. With no `PDK_ROOT`, it discovers the adjacent bundle. The Xschem startup
uses `PDK_ROOT` and the project library paths. Netgen's setup is
`$PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl`; ngspice's model library is
`$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice`. Both are plain files usable
in your own scripts. Generated decks record their selected model and DUT paths;
regenerate or update those paths if you move a saved experiment.

## Source, processing and comparison

The existing workstation PDK came from AICEX's `tests/install_open_pdk.sh`, which
configures open_pdks, runs `make`, and runs `make install`. Its metal-resistor
patch is commented out. The older `clone_open_pdk.sh` uses a prebuilt wulffern/pdk
repository, but that is not the source of this measured installation.

Installed metadata identifies open_pdks commit
`1689ac3f2dc763876eaf967227c7dfe831b031ae` (1.0.608), built with Magic 8.3.541.
Primitive, standard-cell and auxiliary source revisions are retained in
`pdk/sky130A/.config/nodeinfo.json`. Source repositories:
[open_pdks](https://github.com/fossi-foundation/open-pdks),
[Sky130 primitives](https://github.com/fossi-foundation/skywater-pdk-libs-sky130_fd_pr),
[HD cells](https://github.com/fossi-foundation/skywater-pdk-libs-sky130_fd_sc_hd), and
[Xschem Sky130](https://github.com/StefanSchippers/xschem_sky130).

The contest copies the already processed installation **without editing it**.
`pdk/manifest.json` records SHA-256 for every copied PDK/support file. All 4,169
files match the original installation byte-for-byte, including model files and
extraction/LVS decks. Applicable upstream notices are retained and additional
source license copies are in `pdk/LICENSES/`. The PDK's generated startup files
have installation defaults, so direct tool users should export `PDK_ROOT` as
above; the competition never relies on those fallback prefixes.

A separate copy in a cache path containing spaces passed doctor, DRC, LVS, RC
extraction, extracted DC simulation and Xschem netlisting with the original
`PDK_ROOT` unset. Regenerated netlists matched the canonical files. These are
bounded relocation checks, not a repeat of the full 45-condition qualification.
