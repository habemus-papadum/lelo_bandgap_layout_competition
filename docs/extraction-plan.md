# Proposed bandgap competition extraction

Historical plan, 2026-09-26. **The dependency was restored and the user approved
implementation. The extracted project and evaluator are now available; start
with the [README](../README.md) and [journal](journal.md).** The original blocker,
stop decision and proposed implementation sequence below are preserved as the
record of that planning checkpoint. See [dependency-resolution.md](dependency-resolution.md)
for the repair and original-flow evidence, and [packaging.md](packaging.md) for
the actual extraction. The plan incorporated the user's preference for a
portable project, reusable cells, two competition tracks and editable benches.

## Findings and the stop condition

At the preceding checkpoint, the original temperature-sensor flow **did not
complete on this machine**. The missing dependency was `ip/rey_tr_sky130a`,
referenced by the source
IP's `config.yaml` but absent from the parent `ip/config.yaml`. The source design
has a dangling `design/REY_TR_SKY130A` link. Both the top schematic and layout use
`REYTR_ANTX1_CV` for `xant_cmpo_a` and `xant_cmpo_b`.

Fresh command, from `ip/lelo_temp_sky130a/work`:

```sh
make drc cdl lvs CELL=LELO_TEMP
```

This failed after 1.10 seconds. Magic reported:

```text
File ../design/LELO_TEMP_SKY130A/../REY_TR_SKY130A/REYTR_ANTX1_CV.mag couldn't be read
Failure to read entire subtree of cell.
Failed on cell REYTR_ANTX1_CV.
```

Consequently `lvs/LELO_TEMP.spi` was not produced, so Netgen could not compare the
circuits. Xschem also wrote `REYTR_ANTX1_CV IS MISSING !!!!` comments into the
generated CDL. This is an incomplete project dependency, not a demonstrated
electrical mismatch or a reason to redesign the circuit.

The same run's DRC report said zero errors even though it explicitly could not
expand that cell. **That DRC result is invalid for the complete sensor.** The
future doctor and DRC command must establish complete hierarchy loading before
accepting a zero-error result. File existence alone is likewise insufficient to
accept an Xschem netlist.

Per the user's original stop instruction, no dependency was fetched, no circuit
was repaired, and no further executable validation was attempted after this
failure was inspected. Remaining analysis was read-only inspection and planning.
The following table records that checkpoint, before the authorized repair.

| Check | Evidence | Status |
| --- | --- | --- |
| Bandgap Magic DRC | Previous phase: zero errors, 0.89 s | Passed in existing environment |
| Bandgap fresh CDL + LVS | Previous phase: unique match, 6.30 s | Passed in existing environment |
| Full analog core DRC + CDL + LVS | This phase: missing cell, 1.10 s | Blocked; DRC result cannot be accepted |
| Counter/FSM behavioral testbench | `make tb` in `sim/tb_lelo_temp`, 0.65 s | Execution smoke check passed |
| Fresh analog schematic/extracted simulation | Not run | Unverified |
| Full RC extraction and simulation | Source scripts inspected only | Unverified |

The digital spike used the supplied Verilog oscillator model, counter, and FSM.
It produced 166 numeric samples for -40 through 125 C with counts ranging from
61 to 140. Counts are not strictly nondecreasing. No monotonicity assertion or
analog accuracy claim is inferred from successful execution; this is only an
execution smoke check. Plot regeneration was not run.

Observed tools: arm64 host, Magic 8.3.541, ngspice 47. KLayout was not found on
the current PATH; its installation elsewhere was not investigated. The timings
above are single observations, not estimates for all corners or other machines.

## Boundary and dependency inventory

The extraction target is `LELOTEMP_BIAS_IBP`, including the startup circuitry,
`LELOTEMP_OTAR` amplifier, cascode bias generation, resistors, bipolar devices,
capacitors, and four current outputs. Supply, enable/complement, `VD1`, and
loop-access ports `LPI`/`LPO` are part of the interface. The oscillator and digital
counter will not be competition deliverables.

This circuit produces PTAT current and a CTAT voltage. The reference curve is
temperature dependent by design. The competition should preserve that transfer
function and useful dynamic behavior, rather than minimize temperature slope.

A read-only recursive scan of the reference `.mag` hierarchy found:

| Location | Unique local Magic cells |
| --- | ---: |
| `LELO_TEMP_SKY130A` | 22 |
| `REY_ATR_SKY130A` | 23 |
| Total | 45 |

Together these files occupy 113,240 bytes. The remaining leaf is the installed
PDK's `sky130_fd_pr__rf_pnp_05v5_W3p40L3p40`. The scan found no ambiguous local
cell names. This is a layout inventory, not a completed schematic or licensing
audit. It does **not** include the missing `REYTR_ANTX1_CV`: that dependency is
outside the bandgap's scanned layout hierarchy.

Keeping this small hierarchy is preferable to spending effort flattening it.
Copy only its dependency closure, organize it in a couple of library folders,
and preserve relative references. Flattening remains an option if portability
verification exposes a practical reason to do it.

Reusable IP must be delivered as usable artifacts: `.mag`, `.sym`, `.sch`, and
device-level SPICE definitions as applicable, together with a brief pin/device
catalog and placement/tap/orientation guidance. Students must not need cicpy or
the source repositories to instantiate or understand a cell. Include needed
dummy and tap cells; do not silently treat them as empty placeholders.

The current bandgap decks include `LELOTEMP_OTAR_lpe.spi` in the `Sch` branch.
Whether that definition overrides or duplicates the schematic amplifier remains
unverified. Build a clean, fully schematic baseline with every subcircuit
explicitly resolved once. Compare it with the original deck during the remaining
bandgap-specific validation; document any resulting difference instead of
inheriting a mixed view.

The schematic also contains explicit rail-tied filler transistors. Before
freezing the competition netlist, inventory these and define their treatment in
both tracks. Initially preserve them; do not silently delete devices or change
the circuit while extracting it.

## Proposed portable package

This is an organization proposal, not an exact file-count promise:

```text
bandgap/
  README.md                 quick start, tracks, interface, submission contract
  competition.yaml          fixed corners, loads, gates, scoring, provenance
  tools.local.example.yaml  tool and PDK path examples
  .gitignore                tools.local.yaml and generated runs
  schematic/                editable Xschem hierarchy and canonical SPICE
  cells/                    required reusable device/tap cells and short catalog
  reference/                bandgap reference Magic hierarchy
  testbenches/              plain SPICE DC, startup, loop-stability benches
  tools/                    small Python driver plus readable Tcl checks
  docs/                     design explanation, evaluation rules, journal, limits
  LICENSES/                 original notices and attribution where applicable
```

Avoid duplicating the same cell across `cells/`, `schematic/`, and `reference/`:
keep each view in its owning directory and set explicit local search paths.
Preserve source revisions and file provenance. Locate applicable upstream
permission notices before distributing imported material; this review has not
yet established the notice set for every dependency.

External prerequisites are installed tools and a compatible Sky130A PDK.
Vendoring the entire PDK is unnecessary. Pin and report the tested PDK revision
and relevant technology/model/setup file hashes. Resolve local tool/PDK paths
through configuration; no absolute source-repository paths, external symlinks,
parent Makefiles, network downloads, global Xschem setup, or `cic*` commands.

Use Python standard library plus PyYAML for orchestration. Prefer simulator
measurements or simple exported numeric tables over adding a waveform parser.
Keep any plotting dependency optional. Headless evaluation should not require
the Xschem GUI; retain Xschem sources and a local launch/netlisting configuration
for participants who want to inspect and modify schematics.

## Two tracks, one electrical circuit

Recommended starting definitions, to be frozen in the rules before release:

1. **Provided-cell layout:** place and route the supplied immutable device and
   passive tiles, with their documented taps/dummies. Allow legal transformations
   and added interconnect; preserve the required device connectivity and sizes.
   The proposed fixed-cell boundary is the reusable device tiles, not the entire
   bandgap or its amplifier. The reference amplifier remains an example of
   assembly. Publish the exact allowed cell list.
2. **Custom-device layout:** implement the same device-level schematic using
   original geometry or participant-designed tile variants. Match device types,
   dimensions, multiplicities/equivalent parallel devices, connectivity, and
   mandatory pins under the declared LVS rules. Use the installed PDK's primitive
   devices and models in either track; “no predefined IP” here excludes the
   supplied REY/reference layout tiles, not the PDK itself.

Maintain separate rankings. The score, stimuli, extraction recipe, and
electrical checks should otherwise be identical. Changes to transistor sizes or
topology are circuit redesign and fall outside this layout competition.

For the provided-cell track, verify the allowed cells against published hashes
and restrict edits to the declared assembly/interconnect scope. Device-level
LVS remains necessary in both tracks. DRC/LVS cannot establish originality in
the custom track; do not claim they can.

Accept a top Magic file plus any participant-owned local subcells. A single flat
file is also valid. Require a named top cell, a resolved hierarchy, and all
non-PDK dependencies inside the submitted/project directories. Do not impose
the source design's internal instance names on students.

## Separate checks and editable benches

One small driver can expose the following independently runnable subcommands;
each stage's Python/Tcl implementation remains readable and reusable on its own.
An `all` command invokes exactly the same checks in dependency order.

| Check | Responsibility and output |
| --- | --- |
| `doctor` | Tool launches/versions, PDK/model/setup availability, complete cell and include resolution, configuration consistency; no simulation sweep |
| `drc` | Complete hierarchy load, agreed full DRC deck, zero violations; rule descriptions and locations, raw tool log |
| `lvs` | Fresh extracted connectivity against canonical device-level schematic; reject unresolved/empty cells, mismatches, missing/ambiguous ports |
| `area` | Geometry-derived top bounding rectangle in square micrometres, including required taps/guards and all child geometry; do not trust an editable boundary label |
| `extract` | Fresh parasitic netlist, extraction settings, warnings, device/port sanity report and connectivity validation |
| `simulate --view schematic` | DC transfer, startup/settling, supply current/power-down behavior, stability; reference measurements |
| `simulate --view layout` | Same benches, corners, loads, tolerances and measurements using extracted netlist |
| `score` | Check prerequisites/provenance, report each metric, gates and combined score |
| `all` | Run the above with explicit view/profile selections; report per-stage and total time |

Each stage writes to its own run directory: input/settings hashes, tool/PDK
identity, elapsed wall time, exit/result status, and raw diagnostics plus compact
JSON/CSV results. Missing models, incomplete hierarchy, fatal tool diagnostics,
timeouts, missing measurements, and nonfinite values fail the stage. Reusing
results requires matching inputs/settings; a fresh simulation is unnecessary
when only the student's reporting format changes.

The official DRC deck must be declared explicitly. Start by verifying Magic's
full deck; assess whether the source flow's complementary KLayout deck should
also be a mandatory command. Do not advertise foundry signoff coverage from a
single open-source check. Either choice must be documented and timed rather
than hidden in the evaluator.

Keep the supplied DC, transient, and loop-stability stimuli in plain SPICE,
without cicsim preprocessor directives. Provide an explicit DUT include/port
adapter and named parameters. Participants can copy benches and change loads,
ramps, or probes without understanding the orchestration. Measurements for
scoring should use boundary ports, so arbitrary student hierarchy works.
Connect `LPI`/`LPO` normally for DC/transient and through a documented probe for
loop analysis. Preserve an editable Xschem bench where useful; the existing
`TB_LELOTEMP_BIAS_IBP_LSTB.sch` is a candidate to inspect and retain.

Use two explicit profiles: a fast typical-condition development run, and the
official corner grid. Start assessing the source's -40 to 125 C range and
1.7/1.8/1.9 V supplies with tt/ss/ff/sf/fs process models. Decide bipolar,
resistor, capacitor corner combinations from the actual model support, not by
assuming a MOS corner covers every device. Add startup ramps and output loading
conditions that represent the bandgap's intended use. Freeze the grid only after
the baseline works. No hidden per-submission recalibration of the transfer curve.
Monte Carlo can be diagnostic initially; do not introduce random ranking noise.

## RC extraction: known limits and proposed policy

These observations come from the source recipes and comments, not a fresh RC
run in this phase:

- `lpe.tcl` flattens geometry and exports capacitances with
  `ext2spice cthresh 0.01`. It does not invoke the distributed-resistance flow.
  Its `lpe` target removes parasitic capacitor lines for an additional LVS check.
- `lper.tcl` enables resistance, capacitance, and coupling extraction, invokes
  `extresist tolerance 10`/`extresist all`, and exports the resulting netlist.
- The original full-sensor flow documents duplicate device names and diode
  area/perimeter unit conversion before ngspice can use that netlist.
  `fix_lper.py` renames duplicates and scales selected diode parameters.
  These are semantic transformations that require explicit validation; a
  generic “patch whatever makes SPICE run” step is unsuitable for judging.
- The `lper` target's RC-stripping LVS approximation deletes certain resistor
  lines and rewrites node suffixes. Source comments report a structural failure
  because resistor fragments remain. Deleting a resistor is not generally
  equivalent to reconnecting its endpoints. Simulation agreement is useful
  evidence but does not prove connectivity equivalence.
- The source claims a roughly 0.92 RC/C period ratio across selected full-sensor
  cases. That is a historical source claim, not a result reproduced here or a
  bandgap-specific guarantee.

First establish the capacitance extraction path as a reproducible demonstration
and verify it against connectivity LVS. Then qualify full RC on the bandgap:
validate ports/devices, unit handling, duplicate-name handling, extraction
completeness, and a principled reduction/shorting of identified parasitic
resistors for comparison to the canonical schematic. Keep designed resistors
and capacitors distinct from wiring parasitics; never remove them by a broad
name pattern. Exercise a small known interconnect example and the reference
bandgap before using the result for scoring.

**Recommended release gate:** use validated RC for official ranking. A C-only
development evaluator can be useful, but must be labelled as such: it omits
wire-resistance effects and could reward layouts with unrealistically narrow or
long routing. If full RC cannot be qualified in a bounded effort, stop for a
decision about a restricted C-only competition rather than silently substituting
one extraction model for the other. The missing-library problem was independent
of these RC concerns and has since been resolved.

## Proposed figures of merit

Mandatory eligibility: complete hierarchy, DRC, device-level LVS, valid
extraction, completed required simulations, successful startup, and electrical
limits for outputs, settling, stability, and powered-down behavior. Define
physical pin accessibility/shorting requirements as part of the submission
contract. Report all individual metrics even for a disqualified submission.

Proposed dimensionless combined score for qualifying designs, higher is better:

```text
S = 100 * (A_reference / A_layout)
        / ((1 + D^2) * sqrt(r_settle * r_power))

D = max over required corners, temperatures and outputs of:
      abs(I_layout - I_schematic) / allowed_current_deviation
      abs(V_layout - V_schematic) / allowed_voltage_deviation

r_settle = max(1, worst matched-condition t_layout / t_schematic)
r_power  = max(1, worst matched-condition P_layout / P_schematic)
```

Here `A_reference` is a fixed normalization, not a target students must match.
Current allowances can be a fixed fraction of the nonzero schematic output at
the same condition; voltage allowances can be fixed millivolts. Power means
positive active supply power; use separate absolute limits for near-zero
power-down leakage. Settling is the time after the enable event to enter and
remain inside a defined output band, with a sustained hold interval and an
absolute output-validity gate. Ratios require valid positive denominators.

This proposal rewards smaller area while penalizing altered transfer curves and
slower/higher-power operation. Taking the worst deviation prevents one bad
output or corner from being hidden by averaging. Squaring `D` makes large
degradation increasingly expensive; square-root dynamic/power penalties give
area and transfer preservation the dominant role. Faster startup or lower power
remain visible as individual metrics but do not compensate for invalid bias.

The tolerances, gates, and these proposed weights must be tested against fresh
schematic/reference results and sensible hypothetical tradeoffs before being
frozen. Do not invent thresholds that the reference cannot meet or tune them
after seeing competitors. Inspect the instructor's original full-sensor FoM
for context after the validation gate; it has not been evaluated in this phase.

Layout-dependent matching, gradients and thermal effects not represented by
the chosen extraction/device models are limitations of the score. Document
placement/matching practices separately; ordinary PEX should not be presented
as measuring every benefit of good analog layout.

## Implementation order and acceptance criteria

Follow-up status: the missing-library repair and representative full-sensor
schematic/C-extracted runs in step 1 are complete. Bandgap-specific benches,
the clean schematic baseline, and the RC qualification remain to be addressed
after review. The sequence below preserves the proposed release gates.

1. **Resolve the existing-flow stop condition after discussion.** Restore the
   declared missing REY_TR dependency at a recorded revision; rerun full-core
   DRC/CDL/LVS and reject all unresolved cells. Then run representative original
   schematic and capacitance-extracted analog cases, plus bandgap DC/startup/
   stability tests. Verify fresh measurements, not just process exit codes.
   Do not begin extraction until this gate is satisfied or the user explicitly
   changes the prerequisite. A full Monte Carlo campaign is not required just
   to establish that the tooling works.
2. **Freeze the circuit and imported dependency set.** Resolve schematic,
   symbol, netlist, layout, and probe-library closures; record provenance and
   notices. Reconcile schematic versus extracted OTA definitions, filler
   devices, ports, and units. Produce the cell catalog and the two track rules.
3. **Assemble the portable project.** Copy only necessary views and documents,
   keeping the modest reference hierarchy. Supply local Xschem/Magic setup and
   plain-SPICE benches. Match generated canonical netlists against the source
   before changing testbench orchestration.
4. **Implement independently runnable checks.** Start with doctor, hierarchy,
   DRC, LVS and area; add extraction, benches, measurements and reporting.
   Validate capacitance extraction and then qualify RC as described above.
5. **Measure and freeze the judging contract.** Collect schematic/reference
   baselines, select and explain limits/weights, measure stage runtimes, and
   publish the complete configuration and reference results.
6. **Demonstrate portability and failure behavior.** Copy the folder outside
   aicex, remove CIC tools and repo search paths from the execution environment,
   and run using only installed EDA tools and configured PDK. Regenerate the
   schematic netlist there as well. Confirm rejection of a missing child cell,
   deliberate short/open, a known DRC violation, and incomplete simulation
   results. These targeted checks validate the judging contract. Record actual
   timings, remaining limitations, and commands in the journal.

Work is naturally staged; extra agents are not necessary to resolve the present
missing dependency. After validation, dependency packaging and evaluator review
could be independent tasks if the user wants delegation. No agents have been
used in either reconnaissance phase.
