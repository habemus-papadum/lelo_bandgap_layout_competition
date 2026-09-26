# Evaluation contract

The executable contract is [competition.yaml](../competition.yaml), the three
[SPICE benches](../testbenches/README.md), and the small [evaluator](../tools/check.py).
The same commands apply to the reference and participant layouts. Changes to
official limits or code require a new published competition revision.

## Eligibility and coverage

Checks must establish all of the following before a design is scored:

1. The layout contains physical geometry (pin-only starters fail), and every
   layout child resolves with no conflicting cell definitions. The
   provided-cell track also checks immutable tile hashes and rejects new
   device-forming layers in assembly cells. PDK primitive cells come from the
   configured PDK, not similarly named submission files.
2. Magic's Sky130A `drc(full)` deck reports zero errors on the complete layout.
3. Fresh extracted connectivity matches the canonical schematic under the
   installed Sky130A Netgen setup, including device properties. Unresolved or
   empty electrical subcircuits fail before Netgen can treat them as black boxes.
   The six declared PDK device classes are intentional primitive boundaries.
4. The flat parasitic export has the correct eleven pins, unique element names
   and supported device forms. Numeric extracted wiring resistors are shorted
   by connectivity union, numeric wiring capacitors removed, and the reduced
   circuit must match the schematic again. Designed resistors and capacitors
   are PDK `X` devices and are preserved.
5. DC, transient, and stability simulations complete at every selected
   condition with finite measurements. Missing data, incomplete waveforms,
   duplicate model-subcircuit definitions and nonconvergence fail explicitly.
6. Output current/voltage, startup settling, active power, shutdown leakage and
   phase margin meet the published electrical limits in both circuit views.

Magic is the required DRC tool in this version. KLayout and antenna signoff are
not included in the official checks. A pass is not a claim of foundry signoff.
The reference's Magic extraction warnings and resistance-model caveats are
retained and discussed in [rc-validation.md](rc-validation.md).

The reference is checked with the exact installed technology/model/setup files;
their combined SHA-256 is recorded with every result. Tool paths/versions are
reported by `doctor`; binaries, cell contents, benches, evaluator sources and
simulation configuration contribute to the prerequisite signature. No result is
accepted solely because an old log exists. Changes to scoring weights alone
allow existing measurements to be rescored; the score report records the full
scoring configuration and competition-file hash.

## Stimuli and corner grid

The typical development profile uses `tt`, 27 C and 1.8 V. The corner profile
uses five PDK library sections (`tt`, `ss`, `ff`, `sf`, `fs`), three temperatures
(-40, 27 and 125 C), and three supplies (1.7, 1.8 and 1.9 V): 45 combinations
per view. These are the installed `sky130.lib.spice` sections, including their
own non-MOS choices; in this PDK they use typical resistor/capacitor models.
This release does not claim independent resistor/capacitor extremes, Monte
Carlo, mismatch, a continuous temperature sweep, noise, or PSRR qualification.

All comparisons pair a layout result with the schematic at the same condition.
Both views use identical compliance voltages on the four outputs: 0.5, 0.6,
0.7 and 0.8 V. No per-layout fitting or recalibration hides a changed transfer
curve. The clean schematic baseline is generated from the bundled schematic.

The supply ramps over 10 ns. Enable is asserted at 1 us with a 1 ns edge,
deasserted at 10 us, and the transient ends at 12 us. Settling means **all four
currents and VD1** enter a 1% band around the DC operating point and remain
there until disable, with at least a 1 us hold. Shutdown current is averaged
over the final 1 us. A transient-only development run uses its active-tail
mean as the target; it cannot replace a complete DC/transient/stability result
for scoring.

The stability bench uses a two-injection return-ratio probe across LPI/LPO,
sweeping 1 Hz to 1 GHz. It reports the lowest phase margin at descending
unity-gain crossings and the first crossing's frequency. The measurement checks
the low-frequency feedback sign and requires a crossing within the sweep.

## Score

$$
S = 100\frac{A_\mathrm{reference}}{A_\mathrm{layout}}
\frac{1}{(1+D^2)\sqrt{r_\mathrm{settle}\,r_\mathrm{power}}}
$$

Higher is better, with separate provided-cell and custom-device rankings:

```text
score = 100 × (reference_area / submitted_area)
            / ((1 + D²) × sqrt(r_settle × r_power))

D = maximum, across all required conditions and outputs, of:
    |I_layout − I_schematic| / (0.05 × I_schematic)
    |VD1_layout − VD1_schematic| / 0.010 V

r_settle = max(1, worst matched-condition settling_layout / settling_schematic)
r_power  = max(1, worst matched-condition power_layout / power_schematic)
```

The denominator normalizers express tradeoffs, not an assertion that a 5%
current error is a process tolerance. Smaller area improves the score linearly;
large transfer errors incur an increasing penalty. Settling and power penalties
retain a dynamic/energy cost without overpowering area and transfer preservation.
Faster or lower-power operation is still reported individually, but cannot
compensate for incorrect outputs. Leakage and phase margin are eligibility
limits rather than additional weighted terms. An ineligible layout scores zero
and the score command fails.

For example, at unchanged area/power/settling, a maximum normalized error of
0.5 gives 80 points; an error of 1 gives 50. A 20% smaller layout with D=0.5
gives 100. These examples make the chosen tradeoff explicit. The reference's
own score need not equal 100: its real parasitics are penalized too. Only a
complete RC corner-profile result with `scoring.qualified: true` is labelled
official. Other results are explicitly development results.

Area is the bounding rectangle of flattened physical paint, including child
devices, taps and guards. Label extents, checkpaint, `FIXED_BBOX` and other
editable boundary properties do not define the score. The reference area is
10,467.146732 square micrometres on the measured Magic grid.

The original instructor's full-sensor FoM combines duty-cycle average current
and calibrated temperature error. That requires oscillator and counter behavior
outside this competition, so this evaluator measures bandgap transfer fidelity,
settling, power and area directly. See the
[original project specification](https://analogicus.com/aic2026/the_project#figure-of-merit).

## Result files and experiments

Each invocation creates a new stage directory beneath `--out` and updates a
small `<check>.json` pointer/report. Reports include every generated artifact's
hash. Earlier stage directories are retained for diagnosis. Repeated independent
simulation commands replace the selected profile/view report; use a separate
output directory to retain a partial-analysis experiment beside an official run.

The evaluator is inspectable and intended for trusted local execution. It is
not a server sandbox, and the documentation does not claim protection against
students editing the evaluator itself. A hosted judge would use an organizer's
unchanged copy. Physical checks and provenance prevent accidental incomplete,
stale or mismatched results within the declared local workflow.
