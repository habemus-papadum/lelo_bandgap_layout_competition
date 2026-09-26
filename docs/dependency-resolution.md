# Missing REY_TR dependency: cause, repair, and verification

2026-09-26. The user authorized investigating the missing library, adding it to
the parent configuration, and installing it through cicconf. Extraction remains
on hold pending review of these results.

## Result

The missing dependency is resolved. Added `rey_tr_sky130a` to `ip/config.yaml`
and cloned it through the installed cicconf implementation over HTTPS. The
existing `ip/lelo_temp_sky130a/design/REY_TR_SKY130A` symlink now resolves without
modification. No cell substitution, circuit edits, or PDK changes were needed.

Installed repository: <https://github.com/wulffern/rey_tr_sky130a>

Recorded revision: `54c9a13d0106ed2bc26351b59538f699ae54b6b5` (`main`). The parent
configuration follows `main`, consistent with adjacent entries; this revision
records exactly what was verified. The repository contains no Git submodules,
so recursive submodule initialization is unnecessary for this checkout.

## ATR versus TR

The local analog library is named `rey_atr_sky130a`, rather than
`rey_atr_sky130nm`. Both REY libraries target Sky130A, but provide different
collections of cells:

| Library | Role in this project |
| --- | --- |
| REY_ATR | Analog transistor and passive tiles used for the bandgap/amplifier; the source describes low-layer pins and metal left available for routing |
| REY_TR | Analog support standard cells: small logic functions, passives, transistors, taps, and the required antenna diode |

The [upstream TR documentation](https://analogicus.com/rey_tr_sky130a/) describes
it as the second generation of JNW_TR, intended for incidental logic within
analog designs. It is not a synthesis library. There is overlap in cell types
between ATR and TR; they are not interchangeable namespaces.

`REYTR_ANTX1_CV` was not found among the local ATR files. It is supplied by TR
as `.mag`, `.sch`, and `.sym`. Its schematic contains a
`sky130_fd_pr__diode_pw2nd_05v5` diode with ports `A` and `AVSS`. The temperature
sensor instantiates two of these on comparator-related nets. Restoring the
actual dependency therefore preserves the intended circuit and geometry.

## What happened: evidence versus inference

The available Git history supports an entry that was never propagated into the
parent manifest, rather than an entry that was subsequently deleted:

1. Parent aicex commit `9f25b36` (2026-08-05) added `rey_atr_sky130a` to
   `ip/config.yaml`.
2. Sensor commit `a7362ba` (2026-08-06) added `rey_tr_sky130a` to its own
   `config.yaml` and added the design-library symlink, initially for an OTA
   resistor. The present bandgap uses REY_ATR resistors; that historical reason
   should not be mistaken for its current dependency inventory.
3. Sensor commit `5fa9772` (2026-08-14) added the two antenna diode instances.
   Its commit message explicitly says it needs REY_TR revision `bba5854` and
   reports DRC/LVS/antenna checks performed by the author.
4. Searching all available parent Git history with
   `git log --all -S'rey_tr_sky130a' -- ip/config.yaml` found no entry before
   this repair. Both local repositories report non-shallow history.

The installed cicconf reads only the specified YAML file and constructs its
repository list from that file. `clone` does not inspect each cloned IP's own
`config.yaml` for additional dependencies. Thus the documented parent-level
bootstrap could install the sensor while never requesting REY_TR. Git's
`--recursive` concerns Git submodules, not these separate YAML manifests.

There is also a concrete explanation for why CI could miss this discrepancy.
The sensor's LVS workflow calls `jnw-actions`; the inspected action runs:

```sh
cicconf --rundir ../ --config config.yaml clone --https
```

That action runs from the individual IP checkout and therefore reads the sensor
manifest, which *does* list REY_TR. In contrast, aicex's parent-level bootstrap
reads `ip/config.yaml`. The aicex workflow named `LELO` exercises a separate
example/tutorial flow, not this temperature sensor.

An author workstation with REY_TR already present could also mask the omission,
as the user suggested. That is plausible, but the author's filesystem was not
inspected. The recorded commit and differing CI/bootstrap manifests provide
direct evidence without relying on that hypothesis. Historical CI executions
were not audited here.

## Confirmed cicconf weakness

The clone implementation catches a Git failure and renders a failed row, but
the top-level command does not propagate that failure as a nonzero exit status.
An isolated, network-free probe used a nonexistent local repository path:

- Git failed with status 128.
- cicconf displayed `must_fail` / `failed`.
- The cicconf process exited **0**.

The probe used a temporary directory and did not touch project repositories.
This is a genuine automation failure-reporting bug. It did not cause this
particular omission: the parent config never requested REY_TR in the first
place. Neither error propagation nor transitive dependency resolution was
changed as part of this focused repair.

The previously observed DRC false pass on an unloaded child cell is another
independent issue. Restoring the missing cell makes that specific false-pass
condition disappear; the eventual competition doctor must still reject any
incomplete hierarchy before accepting a DRC result.

## Repair procedure

Added the following alongside REY_ATR in the parent `ip/config.yaml`:

```yaml
rey_tr_sky130a:
  remote: git@github.com:wulffern/rey_tr_sky130a.git
  revision: main
  description: Standard cells and antenna diodes used by lelo_temp_sky130a (sky130A)
```

For this targeted installation, serialized just that entry from the updated
manifest into a temporary YAML file, then ran:

```sh
.venv/bin/cicconf --config /temporary/path/config.yaml --rundir /absolute/path/aicex/ip \
  clone --https --no-onclone --jobs 1
```

This uses cicconf's normal clone/configuration path while avoiding unrelated
missing repositories. The normal documented `cicconf clone --https` invocation
from `ip/` will include REY_TR in future bootstraps. The sensor's own config
already contained the entry and required no edit.

## Fresh verification after installation

All commands ran against the existing source sensor and original Makefiles.
Cache reuse was disabled for both simulations with `--no-sha`.

| Command and working directory | Wall time | Verified outcome |
| --- | ---: | --- |
| `make drc cdl lvs CELL=LELO_TEMP` in `work/` | 2.64 s | Complete hierarchy; zero Magic DRC errors; fresh CDL; LVS matches uniquely |
| `make typical TB=calibrate VIEW=Sch THREADS=1 'PROGRESS=--no-progress --no-sha --timeout 120'` in `sim/LELO_TEMP` | 11.38 s | Fresh schematic transient simulations and measurements at 25 and 85 C |
| `make typical TB=calibrate VIEW=Lay THREADS=1 'PROGRESS=--no-progress --no-sha --timeout 180'` in `sim/LELO_TEMP` | 8.40 s | Fresh capacitance extraction, extracted-netlist LVS match, transient simulations and measurements at 25 and 85 C |

Conditions: typical process, nominal 1.8 V, source calibration bench (7 us
transient with enable at 2 us). Timing includes Make prerequisites and
postprocessing; it is one observation, not a performance comparison of views.

Measured frequency uses four periods between the first and fifth rising edges:

| View | Temperature | Frequency | Active supply current | CTAT voltage |
| --- | ---: | ---: | ---: | ---: |
| Schematic | 25 C | 2.4177 MHz | 84.384 uA | 0.742143 V |
| Schematic | 85 C | 3.2365 MHz | 103.884 uA | 0.641465 V |
| Extracted C | 25 C | 1.9886 MHz | 83.067 uA | 0.742143 V |
| Extracted C | 85 C | 2.6582 MHz | 103.344 uA | 0.641453 V |

Checked measurement values for finiteness, correctly ordered edges inside the
measurement interval, and plausible supply/output signs and ranges. Inspected
the raw simulation logs and both connectivity reports, not just wrapper exit
codes. The new complete logs contain no missing-cell diagnostics.

Ngspice's separate measurement-only invocation emits an “incomplete or empty
netlist” message after loading the transient data and completing measurements.
That deck intentionally contains only control commands, and the existing cicsim
code recognizes this behavior in ngspice 45 and later. This does not indicate a
failed DUT simulation: both fresh main simulation logs contain transient data
and the expected measurement results were checked. Device-model warnings also
remain in the original flow; no unrelated warning cleanup was attempted.

The original flow is now demonstrated through representative physical checks,
schematic simulation, capacitance extraction, extracted simulation, and the
earlier digital execution smoke test. This is **not** a completed all-corner,
Monte Carlo, KLayout DRC, full RC, or standalone bandgap-bench qualification.
Those limits remain explicit in the extraction plan.

Logs, timing JSON, measurement snapshots, and the clone-failure probe are at
`/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-dependency-2n009hk4/`.
Normal generated outputs remain under the source `work/` and simulation
directories. The pre-existing untracked `sim/LELO_TEMP/xdut.spi` was backed up
and verified byte-identical after the runs. No tracked source-IP files changed.
