# RC feasibility and standalone bench validation

2026-09-26. This investigation ran in an isolated temporary directory; the source
IP and its shared generated files were not changed. Parent-level integration and
corner qualification are recorded separately in the journal.

## Result

The bandgap's distributed RC path works without the full sensor's duplicate-name
or antenna-diode unit repairs. A principled electrical contraction of parasitic
resistors passes LVS. Fresh clean-schematic and extracted-RC operating-point,
startup/shutdown, and loop-stability simulations all pass the standalone benches.
This was a bounded feasibility exercise, not a modification of the source
circuit or its PDK.

| Fresh artifact | Designed device instances | Numeric parasitic resistors | Numeric parasitic capacitors |
| --- | ---: | ---: | ---: |
| Capacitance extraction | 228 | 0 | 729 |
| Distributed RC extraction | 228 | 6,746 | 2,129 |

Both raw exports have the correct eleven top-level ports in canonical order,
including the four `IBP_1U<…>` ports. Only the generated `_flat` top name needs
normalization. No missing terminal is repaired by replacing the port header.
The raw exports contain no duplicate device names and no antenna diodes.
The circuit's PNP devices already use the proper PDK subcircuit models.

## Extraction recipe and connectivity evidence

Magic 8.3.541 was run with the installed Sky130A startup file and explicit
project cell paths. After flattening the reference into an isolated scratch
cell, the RC commands were:

```tcl
extract do resistance
extract do capacitance
extract do coupling
extract all
ext2sim labels on
ext2sim -p <extraction-directory>
extresist tolerance 10
extresist all
ext2spice lvs
ext2spice cthresh 0.01
ext2spice extresist on
ext2spice -p <extraction-directory> -o <raw-netlist>
```

These are the original source flow's extraction settings. The C-only
comparison omits extresist and sets `ext2spice extresist off`. Extraction took
approximately 0.27 s for each mode in the initial isolated run. Magic reports
46 output resistance networks out of 256 nets; “RC” denotes the selected,
thresholded distributed model, not a claim that every physical conductor has
an independently retained resistor. The export retains capacitances above the
0.01 fF threshold.

For connectivity comparison, a union-find data structure joins the endpoints of
each **numeric four-token parasitic resistor**. The comparison netlist rewrites
the primitive device terminals to those equivalence classes and removes numeric
parasitic capacitors. Deliberately designed resistors and MIM capacitors are
`X` instances of named PDK models and remain intact. The implementation rejects
unsupported element forms and distinct top ports joined by contraction.
It never deletes a resistor without reconnecting its endpoints.

Both the reduced C-only netlist and the contracted RC netlist **match uniquely**
against the original bandgap's device-level CDL, including terminal identities
and the PDK's device parameter rules. Netgen takes approximately 0.03 s in this
small example. These checks address the source's known failure of deleting
resistor lines and heuristically stripping node suffixes.

## Small interconnect cross-check

A separate fixture copies one two-finger NFET tile into scratch space and adds
a 0.6 um wide metal1 gate route. Its extracted RC model contains ten parasitic
resistors and twelve capacitors. Reducing it through the competition's actual
`contract_parasitics` function matches the C-only device connectivity uniquely.

Lengthening only the metal1 route by 50 um changes the route's series resistance
from 123.370 to 133.786 ohms. The 10.416 ohm increase agrees with
`0.125 ohm/square × 50 um / 0.6 um = 10.4167 ohms`; the contact/poly contributions
and other resistors remain unchanged. This verifies a simple resistance scale
and a real gate connection, alongside the bandgap's connectivity check.

An earlier bare-wire trial with two differently named ports on the same
conductor triggered Magic's electrically-shorted-port diagnostics and produced
parallel resistance branches. Such a submission is rejected by the project's
port/connectivity checks. The usable cross-check uses one external gate port
and actual transistor terminals, avoiding that degenerate case.

## Clean schematic versus the original mixed view

The original bandgap `Sch` decks include `LELOTEMP_OTAR_lpe.spi` before including
the bandgap schematic netlist, which also defines `LELOTEMP_OTAR`. A small
independent duplicate-subcircuit experiment proves that ngspice 47 keeps the
**first** definition and warns that the second definition is ignored. Thus the
original `Sch` bench genuinely uses an extracted amplifier, not a fully
schematic amplifier.

The competition's canonical netlist includes each schematic subcircuit once.
The evaluator rejects subcircuit-redefinition diagnostics. An isolated repeat
with the original include ordering and an extracted OTA, under the new bench's
same four loads and models, gives phase margin 56.545 degrees and unity gain
6.075 MHz. The fully schematic version gives 59.541 degrees and 6.381 MHz.
These different results confirm that removing the mixed view matters. They are
not an exact reproduction of the old published table, whose loading/model
setup differs from the new explicit bench.

## Fresh typical measurements

Conditions: PDK `tt` library section, 27 C, 1.8 V; outputs clamped at 0.5, 0.6,
0.7, and 0.8 V. Each simulator used one thread and KLU. Timings below include
loading the PDK and measurement validation, with the two views running
concurrently, so they are observations rather than machine-independent limits.

| Metric | Clean schematic | Reference RC |
| --- | ---: | ---: |
| Output 0 current | 1.185635 uA | 1.152103 uA |
| Output 1 current | 1.185424 uA | 1.151909 uA |
| Output 2 current | 1.185206 uA | 1.151709 uA |
| Output 3 current | 1.184981 uA | 1.151502 uA |
| VD1 | 0.738866609 V | 0.738316807 V |
| Active power | 74.2328 uW | 72.7987 uW |
| Joint 1% settling after enable | 0.43479 us | 0.64832 us |
| Shutdown supply current | 3.742 nA | 4.361 nA |
| Phase margin | 59.541 degrees | 59.920 degrees |
| Unity gain frequency | 6.381 MHz | 4.928 MHz |
| DC runtime | 10.61 s | 14.17 s |
| Transient runtime | 11.00 s | 18.92 s |
| Stability runtime | 10.97 s | 17.92 s |
| Complete typical suite | 32.58 s | 51.01 s |

The RC result reduces DC current by about 2.83%, despite the C-only transient's
steady-state currents matching the schematic closely. Its startup is slower.
A C-only ranking would miss these routing-resistance effects. The initial RC
transient without KLU took roughly 30 s; using KLU reduced that to roughly 17 s
for the same initial 10 us spike, before shutdown was added.

## Remaining limits and diagnostics

Targeted measurement-failure probes also passed: truncating the transient,
introducing a late output excursion after an apparent early settling event,
replacing the active outputs with zeros, truncating the AC frequency range, and
omitting a numerical table all cause explicit failure. These probes operate on
copies of fresh simulation data; the original measurements remain intact.

- Both flattened extraction modes report 78 feedback warnings from the
  reference geometry: dummy resistor geometry with “device missing 2
  terminals”, and dummy transistor geometry with one missing terminal tied by
  extraction to VSS or VDD. LVS matches the source's intended circuit with this
  PDK handling. These are preserved diagnostics, not silently repaired models.
- RC also warns about a `viali` rectangle at internal coordinate (7238, 21113)
  smaller than the extraction section allows. The reference still passes DRC
  and both connectivity comparisons, but that warning limits claims of exact
  contact-resistance fidelity. No PDK or reference geometry was edited to hide
  it. The evaluator retains the complete extraction log and extraction files;
  the spike also saved the detailed Magic feedback. For additional local
  geometry diagnostics, add `feedback save feedback.txt` before the final
  completion marker in a copy of `tools/physical.tcl`.
- The PDK emits unsupported optional resistor-model parameter warnings in
  ngspice. The benches retain those logs; unknown subcircuits, failed analyses,
  redefined subcircuits, missing tables, incomplete time/frequency ranges, and
  nonfinite values fail the evaluation.
- This validates reproducibility, device connectivity, one resistance scale,
  and simulation feasibility. It does not establish foundry-signoff extraction
  accuracy, layout-dependent mismatch, thermal behavior, or all combinations of
  passive and bipolar process variation.
- Corner results are deliberately not asserted here until the integrated
  driver completes them. The default library-section grid retains typical
  resistor/capacitor process models, as explained in the bench README.

Initial raw evidence, Tcl files, generated decks, full logs, waveform tables,
and the interconnect fixture are under:

```text
/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-rc-0et4rwaz/
```

The portable benches and evaluator are the durable reproduction mechanism;
this temporary evidence directory is not a runtime dependency.
