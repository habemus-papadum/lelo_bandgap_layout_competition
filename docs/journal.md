# Bandgap competition journal

This is a chronological record; early pauses and proposed checks describe their
respective checkpoints. For the implemented project, start with the
[README](../README.md), [evaluation contract](evaluation.md), and
[reference results](reference-results.md). The final entries below record the
authorized extraction and qualification.

## 2026-09-26 — Agreed scope and initial reconnaissance

This entry records the starting agreement. This session is deliberately limited
to documentation review and small investigative runs, followed by discussion.
No extraction or evaluator implementation is authorized for this short phase.
No additional agents are being used.

### Starting agreement

1. Verify the existing `ip/lelo_temp_sky130a` temperature-sensor flow on this
   machine: bandgap, oscillator, and frequency-to-digital logic. Focus on the
   overall tooling and flow rather than minor test failures or recent small
   bugs. If the overall flow does not work, record the evidence and stop before
   extraction so we can discuss it. Existing published results do not count as
   a fresh verification on this machine.
2. Subsequently extract the bandgap into `competitions/bandgap`, with the minimal
   schematic, required circuit definitions, design documentation, and one
   demonstration Magic layout. The schematic and specification are primary;
   the reference layout is secondary.
3. Remove dependencies on the `cic*` tools from the extracted competition.
   Evaluation should use understandable Bash or Python and mainstream
   dependencies, invoking the underlying circuit tools directly. Participants
   must be able to inspect the judging logic and assess its fairness.
4. Provide checked-in YAML competition configuration and, if needed, an ignored
   local YAML file for tool and PDK locations. Provide a doctor check for usable
   tools, models, configuration, and dependencies.
5. Evaluate participant Magic layouts with mandatory **DRC and LVS**, parasitic
   extraction, schematic and extracted simulations, and individual figures of
   merit including area and electrical degradation. Propose an engineering-based
   combined score after understanding the circuit. Offer individually runnable
   checks as well as an optional complete flow; retain useful diagnostics so
   students can adapt checks for local debugging. Record reference-layout
   timings with conditions so students can budget their iteration time. The
   official evaluator may eventually run on a protected server, but server
   infrastructure is outside scope.
6. Maintain this journal under `competitions/bandgap/docs`, recording actual
   actions, outcomes, limitations, and eventual extraction steps. Keep files
   below roughly 1,000 lines and split with a linked summary if needed.

Suggested evaluation structure: DRC, LVS, and basic electrical functionality
are eligibility gates, followed by scoring of qualifying designs. Exact rules,
loads, corners, extraction settings, metrics, weights, and timing measurements
remain to be established.

### Actions and observations

- Checked repository status (initially clean) and searched for applicable
  `AGENTS.md` instructions; none found in this repository or ancestor locations
  checked.
- Read the source README, configuration, layout-flow document, bandgap testbench
  report and Makefile, full-sensor Makefile, and root tooling documentation.
- Located Magic, ngspice, Netgen, Xschem, and Icarus Verilog in
  `/Users/nehal/opt/eda/bin`; `cicsim` is available in the repository `.venv`.
  Executable discovery alone does not establish working tools or a working PDK.
- The source layout-flow document uses `make mag`, `drc`, `gds kdrc`, `cdl lvs`,
  and `ant` from `work/`. Layout generation currently depends on cicpy; these
  generation dependencies need not be carried into a submission evaluator.
- The existing bandgap testbench is named `LELOTEMP_BIAS_IBP` and contains DC
  temperature, transient settling, and loop-stability analyses. Its published
  report includes some out-of-spec values, so those old thresholds should not
  automatically become competition eligibility limits.
- The full-sensor Makefile explicitly describes extracted simulation suites as
  taking hours. It also documents repairs to RC extraction and a structural
  failure of its RC-netlist LVS-stripping path. This needs investigation during
  full validation; it is not evidence that every extraction/LVS path is broken.

### Fresh checks on this machine

Source IP revision: `e439fe6b9351ea47a288847131337f483b2dbfcd`.
The source IP already had an untracked `sim/LELO_TEMP/xdut.spi` before the
spikes; it was left untouched. The parent repository status did not expose it.

Commands below ran in `ip/lelo_temp_sky130a/work`, using existing installed
tools, PDK, library links, and source layout. Each subprocess had a 45-second
timeout; neither reached it. Timings are single wall-clock observations,
including Make overhead, not calibrated competition benchmarks.

| Command | Time | Observed result |
| --- | ---: | --- |
| `make drc CELL=LELOTEMP_BIAS_IBP` | 0.89 s | Magic `drc(full)`: `Total DRC errors found: 0` |
| `make cdl lvs CELL=LELOTEMP_BIAS_IBP` | 6.30 s | Fresh netlisting and comparison: `Final result: Circuits match uniquely.` |

The actual reports were inspected, not just command exit statuses. DRC also
printed timestamp-mismatch messages and a `logcommands` usage message; it
continued through the check and reported zero errors. These were not repaired.
No KLayout DRC run was performed in this short phase.

Native reports are under source `work/drc/LELOTEMP_BIAS_IBP_drc.log` and
`work/lvs/LELOTEMP_BIAS_IBP_lvs.log`. Captured command output is temporarily at
`/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-recon-vf7otbvb/`
(`bandgap-drc.log` and `bandgap-lvs.log`). Those temporary logs are not portable
deliverables. The checks generated working artifacts, but no tracked source-IP
files changed; the only parent-repository addition is this competition journal.

**Verification status: partial.** No fresh analog simulation, parasitic
simulation, full-sensor DRC/LVS, or digital-counter simulation has been run.
The overall original flow is therefore not yet verified. No overall-flow
blocker was demonstrated by these two checks. Extraction has not started.

### Implications for the eventual extraction

- `LELOTEMP_BIAS_IBP` is the bandgap core instantiated by `LELO_TEMP.sch`.
  Its design note explains a PTAT current and CTAT voltage, with startup
  circuitry. Scoring it as a temperature-invariant voltage reference would
  reward the wrong behavior. Candidate metrics are current/voltage transfer
  fidelity over temperature and supply, startup/settling, power, and area.
  A final score and weights require fresh baseline measurements.
- The top `.mag` has 11 direct subcell instances and further library hierarchy.
  Copying that one file alone will not produce a standalone demonstration.
  A flattened reference layout is a plausible way to meet the one-layout-file
  objective, but must be rechecked for DRC and LVS after flattening.
- The native schematic also references reusable device and amplifier cells.
  Extraction must resolve the dependency closure, retain attribution/licenses,
  and provide an authoritative simulation/LVS netlist alongside a readable
  schematic. No dependency closure or license audit has yet been completed.
- The current bandgap DC and transient decks include an extracted
  `LELOTEMP_OTAR_lpe.spi` even in their `Sch` branch. Before calling a result
  a schematic baseline, inspect the generated netlist and determine whether
  this creates a mixed schematic/extracted baseline. Do not copy this pattern
  unquestioningly into the competition.
- Existing Make checks are useful wrappers but unsuitable as an unchanged
  judging contract: the DRC recipe follows its failing report parser with
  `|| tail`, which can return success after reporting a DRC failure. The
  KLayout recipe similarly has `|| true`. Official checks must reject failed
  checks, missing outputs, tool errors, and incomplete runs reliably.
- A natural command split is `doctor`, `drc`, `lvs`, `extract`,
  `simulate-schematic`, `simulate-layout`, and `score`, plus an `all` wrapper.
  Each should preserve raw diagnostics and report elapsed time. Reuse of
  outputs needs explicit provenance so a score cannot silently use stale data.

### Checkpoint and proposed next allocation

Stop here for discussion, as requested. The next bounded phase should finish
validation of the existing flow before building the competition: full-core
DRC/LVS, a digital testbench smoke run, and representative schematic/extracted
analog runs with their prerequisites. Investigate the documented RC-path
limitation separately from the simpler capacitance extraction path. If an
overall-flow blocker emerges, stop and report it rather than undertaking a
repair campaign.

After that gate passes, dependency extraction and evaluator design can be
scoped with evidence. Multi-agent work and a larger simulation budget remain
discussion items; none were used or assumed in this phase. The existing
full-sensor Makefile's hours-long extracted suites should not be confused with
the sub-second/few-second bandgap physical checks measured above.

## 2026-09-26 — Portable-project plan and original-flow blocker

User steering: retaining a small layout hierarchy is acceptable; usable device
IP should be bundled, with provided-cell and custom-device competition tracks.
The copied competition folder must run without aicex/CIC infrastructure (given
installed tools/PDK). Keep editable, clean testbenches and document RC limits.
This phase still stops before actual extraction.

Detailed findings and the proposed contract/implementation sequence are in
[extraction-plan.md](extraction-plan.md).

- Ran `make drc cdl lvs CELL=LELO_TEMP` in source `work/` (1.10 s, failed).
  The full sensor uses `REYTR_ANTX1_CV` but `ip/rey_tr_sky130a` is absent.
  Its declaration exists in the source IP config, not the parent IP config;
  the source design's REY_TR link is dangling. Magic could not load the
  complete subtree and produced no LVS netlist. Xschem's fresh CDL also
  contained explicit missing-cell comments. DRC reported zero errors despite
  that missing geometry, so its full-sensor result is invalid.
- In an independent spike, ran `make tb` in `sim/tb_lelo_temp` (0.65 s, success).
  The behavioral oscillator/FSM/counter run generated 166 numeric temperature
  samples, -40 to 125 C, counts 61 to 140. This is an execution smoke check,
  not an analog accuracy validation; the counts are not strictly monotonic.
- **Stopped executable validation once the missing-dependency failure was
  inspected**, honoring the original stop condition. No clone, repair, analog
  simulation, extraction into the competition, or evaluator implementation
  followed. The complete original flow remains blocked/unverified.
- Read-only layout dependency inventory: 45 local `.mag` files (22 source-IP,
  23 REY_ATR), totaling 113,240 bytes, plus a PDK bipolar leaf. The missing
  REY_TR cell is outside this bandgap layout closure. Keeping the reference
  hierarchy is therefore a reasonable default.
- Reviewed the C and RC extraction recipes, unit/name repair script, bandgap
  benches, source amplifier documentation, reusable-cell README, and local
  dependency declarations. RC behavior remains source-documented, not freshly
  measured. The plan distinguishes a C-only development path from qualified RC
  for ranking and records the unresolved schematic-baseline issue.
- Proposed a small portable package, concrete track definitions, independent
  checks, a worst-condition degradation/area score, and a final copied-folder
  acceptance run without repository/CIC paths. Thresholds remain provisional
  pending actual baseline simulations.

Command logs and timing JSON are temporarily retained in
`/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-plan-7r0pcs3x/`.
Copies of the detailed DRC/extraction logs are there too. The new untracked
digital executable and CSV were moved there after inspection to leave the
source working tree as found; ignored tool output remains in source work
directories. No tracked source-IP files changed. The pre-existing untracked
`sim/LELO_TEMP/xdut.spi` remains untouched.

Next discussion: restoring the missing dependency and completing validation
before extraction. The detailed plan is ready for review; no additional agents
or long simulation suite were started.

## 2026-09-26 — Missing library restored and workaround verified

The user authorized tracing the ATR/TR distinction and missing dependency,
adding the appropriate manifest entry, and installing the library through
cicconf. Extraction remains on hold for the requested review.

- Added `rey_tr_sky130a` to parent `ip/config.yaml`; the sensor's own config
  already listed it. Installed only that entry through cicconf over HTTPS,
  without fetching unrelated repositories. Revision:
  `54c9a13d0106ed2bc26351b59538f699ae54b6b5`. The existing design symlink now
  resolves and supplies the expected antenna diode schematic/symbol/layout.
- ATR supplies analog device tiles; TR supplies support standard cells and
  the missing `REYTR_ANTX1_CV`. No substitution or circuit edits were required.
- History shows ATR added to the parent manifest on August 5, TR added to the
  sensor manifest on August 6, and antenna diode instances added August 14.
  No TR entry was found in available parent history before this repair.
  cicconf does not recursively discover per-IP YAML dependencies. The sensor's
  CI reads its own manifest, which explains how that path could work while
  parent bootstrap missed TR. A pre-existing author checkout remains plausible
  but is not necessary to explain the evidence.
- Confirmed a separate cicconf bug using an isolated nonexistent-local-repo
  probe: Git fails with 128, cicconf prints failure, but cicconf exits 0.
  Documented without broadening this repair into a downloader rewrite.
- Fresh full-core DRC/CDL/LVS passed in 2.64 s, with complete hierarchy,
  zero DRC errors, and a unique LVS match.
- Fresh typical-process/1.8 V calibration runs at 25 and 85 C passed on the
  schematic (11.38 s) and C-extracted view (8.40 s), with caching disabled.
  The extracted netlist also passed its connectivity LVS check. Frequencies
  were 2.418/3.236 MHz schematic and 1.989/2.658 MHz extracted. This restores
  representative original-flow operation; full corner/RC qualification is not
  claimed. No competition files were extracted or evaluator code implemented.

See [dependency-resolution.md](dependency-resolution.md) for root-cause evidence,
commands, measured results, log locations, and remaining limits. The earlier
extraction plan now links to this resolved status. No tracked source-IP files
changed; the existing untracked `xdut.spi` was verified unchanged.

## 2026-09-26 — Standalone implementation and parallel validation

The user approved extraction with two agents: packaging and RC/testbench
validation, followed by integration and corner qualification. This supersedes
the earlier pause before extraction. No source-IP design or generated work
directories are modified in this phase; experiments use private run folders.

- Packaged the reference's 45 local Magic files and the required editable
  schematic/symbol closure. Reusable tiles have standalone electrical views,
  a catalog, source revisions and content hashes. Preserved the schematic's
  explicit filler devices. The installed PDK remains the only external design
  library. See [packaging.md](packaging.md) and [cells.md](cells.md).
- Generated separate canonical simulation and LVS views using a local Xschem
  configuration. Regeneration is byte-identical in an asset-only copy outside
  aicex. The original band's `Sch` include ordering selects an extracted OTA;
  the new canonical baseline is fully schematic, with the difference measured.
- RC feasibility passed: 228 designed device instances, 6,746 wiring resistors,
  and 2,129 wiring capacitors. A union-find contraction shorts only numeric
  wiring resistors while preserving designed PDK resistor/capacitor devices;
  the reduced circuit matches uniquely. A separate physical interconnect fixture
  verifies the expected resistance increment for an additional 50 um of metal1.
  See [rc-validation.md](rc-validation.md).
- Implemented independent doctor, DRC, LVS, area, extraction, simulation and
  scoring commands, plus `all`, using Python/PyYAML and direct Magic/Netgen/
  ngspice calls. Both full suites and individual analyses are selectable.
  Inputs and retained outputs are hashed to reject stale results. Geometry area
  does not trust labels or editable bounding-box properties.
- Fresh typical DC/startup/stability suites pass for the clean schematic and
  RC reference. Nominal RC current is approximately 2.83% below schematic and
  settling is slower; C-only extraction would miss the current effect.
- Independent acceptance review exercised missing/ambiguous/external cells,
  changed fixed tiles, real DRC/LVS faults, spoofed area properties and stale
  outputs. Integration caught a report self-hashing mistake (the wrapper
  overwrote a simulation report after hashing it); fixed by excluding only the
  wrapper's own report from its artifact map. Subsequent grid runs use the fix.
  The maintained [acceptance suite](../tests/acceptance.py) contains meaningful
  positive and negative checks, detailed in [acceptance.md](acceptance.md).
- Read the instructor's original online FoM: duty-cycle average current times
  calibrated temperature error. The bandgap-only score instead combines area,
  matched-condition transfer deviation, settling and active power. The rationale
  and explicit formula are in [evaluation.md](evaluation.md), with a source link.
- Started the integrated 45-condition schematic/RC qualification grid. Final
  results, timings and eligibility limits will be recorded after completion.

## 2026-09-26 — Qualification complete and competition baseline frozen

- The integrated `all --profile corners` run passed every stage: doctor,
  zero-error Magic DRC, unique connectivity LVS, paint-area measurement,
  distributed RC extraction with a second contracted-connectivity LVS, and
  DC/transient/stability analysis at all 45 conditions in each circuit view.
  This is 90 circuit conditions and 270 analyses. The declared grid is
  tt/ss/ff/sf/fs × -40/27/125 C × 1.7/1.8/1.9 V, with the installed library
  sections' typical passive models. It does not establish independent passive
  extremes, Monte Carlo, or full-sensor RC qualification.
- Finalized the source's 45-degree minimum phase margin and 2 us maximum
  settling time after both views passed them. Kept the explicit broad current,
  voltage, power and leakage gates; a 100 nA leakage gate would reject the
  unchanged schematic at hot/fast conditions. Published the 5% current and
  10 mV voltage scoring scales and the area/transfer/settling/power formula.
- Changed only scoring configuration after the numerical run, then reran
  `score --profile corners`. All input/artifact checks passed and the qualified
  reference score is **57.419990**. The measured reference area is
  **10467.146732 um²**; the worst matched-condition output-current deviation
  is **3.0199%**, VD1 difference **0.746559 mV**, and settling ratio **1.62833**.
- The schematic grid took 425.85 s and the RC grid 778.05 s with four concurrent
  cases. The summed complete-stage time is 1215.50 s, approximately 20.3 min.
  The independent copied-project typical flow took 110.90 s, approximately
  1.8 min. Each reference physical check took under one second. These are
  observations on this Apple M5, not portable runtime guarantees.
- Verified the complete typical flow in a fresh virtual environment containing
  only PyYAML, with CIC absent from PATH and no source-repository imports.
  Both canonical schematic views regenerated byte-identically there. Also
  checked independent C-only extraction/DC and flattened custom-track DRC,
  LVS and RC extraction. All passed.
- The maintained acceptance suite passed all 16 checks in 5.73 s, including
  intentional physical shorts, dimension mismatch, DRC violations, unresolved
  hierarchy, altered artifacts and invalid simulation data. Review clarified
  custom-cell naming and the distinction between editable schematic sources
  and the fixed SPICE views used for judging.
- Published [reference results and timings](reference-results.md) and the
  [90-row numerical baseline](reference-results.csv). Raw logs, generated decks,
  waveform tables and hashed reports remain in ignored `runs/qualification`.
  [RC limitations](rc-validation.md), the [evaluation contract](evaluation.md),
  [packaging record](packaging.md), and [acceptance record](acceptance.md) describe
  the evidence and boundaries in detail. The package has no source symlinks;
  the installed Sky130A PDK is its only external circuit library.

No tracked source-IP files changed during extraction. The earlier authorized
parent manifest addition for REY_TR remains this task's only change outside
the new competition folder. Unrelated `spikes/julia-v0` files appeared during
the work and were left untouched. No hosted judge or submission service was
implemented.

## 2026-09-26 — Standalone uv project, CLI and documentation publication

The user explicitly requested extracting this folder to a public personal
GitHub repository named `lelo_bandgap_layout_compeititon`, retaining that spelling,
with a local checkout under `~/src`. The standalone project is now at
`~/src/lelo_bandgap_layout_compeititon`; earlier journal paths refer to the
original aicex workspace. The source competition folder was preserved.

- Added `pyproject.toml`, a committed `uv.lock`, a default Python version and
  the `uv run bandgap` console command. Runtime dependencies are Typer and
  PyYAML; MkDocs/Material dependencies are in a separate `docs` group. Removed
  the redundant requirements file and updated current command examples to uv.
- Kept the CLI adapter small: it delegates to the existing physical/numerical
  evaluator and exposes named commands, typed options, `--help` and `help`.
  It also exposes netlist regeneration and the existing acceptance checks.
  The underlying four evaluator files and canonical circuit assets are unchanged.
- Added four CLI contract tests for tool-free help, argument forwarding,
  invalid requests, auxiliary commands and exact failure-code propagation.
  They pass without a PDK. All 16 real-tool acceptance checks passed through
  the uv CLI in 4.72 seconds. Both schematic views regenerated byte-identically.
- Organized every existing Markdown document into Material navigation, with
  short first-run and CLI guides, competition rules, measured evidence,
  development instructions, and the detailed history/provenance collection.
  Source documents remain single files; a build hook stages public assets.
  LaTeX/MathJax, Mermaid, search, dark mode, code copying, tabs, footnotes and
  admonitions are enabled. A strict local documentation build passes.
- Added GitHub Actions to install locked dependencies, run the tool-free CLI
  tests, build all docs strictly, and deploy main-branch artifacts to Pages.
  Pull requests build and test without deployment. Hosted CI does not claim
  DRC or analog qualification because it has no EDA/PDK installation.
- Preserved imported design attribution and source hashes. Converted only the
  results CSV's line endings to LF and updated its documented SHA-256; its
  numerical values did not change. Raw historical runs and local tool paths
  were excluded from publication, as were Python environments and build output.

The complete typical flow also passed through `uv run bandgap all`, including
doctor, DRC, LVS, RC extraction, both simulation views and scoring. Its
development score is 62.042339, matching the original typical baseline.
The previous 45-condition qualification remains historical evidence; this
interface/documentation migration did not rerun the full grid.
