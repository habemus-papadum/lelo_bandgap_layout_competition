# Editable bandgap benches

These are ordinary ngspice decks with visible `@NAME@` substitution points for
model path, DUT path, process, temperature, supply, and stimulus times. The
Python runner writes a complete `case.spice` beside each `ngspice.log` and data
table. Copy that generated deck, edit it, and run:

```sh
ngspice -n -D ngbehavior=hsa -D skywaterpdk -b case.spice
```

No CIC directives or Python waveform package are involved. `-n` ignores user
startup files so the official run does not inherit personal simulator settings.
KLU is selected in the decks; each simulator uses one thread. Independent corner
cases may run concurrently. Every bench observes only declared DUT ports.

The top instance connects the canonical ports in this exact order:

```text
VDD_1V8 LPI IBP_1U<3> IBP_1U<2> IBP_1U<1> IBP_1U<0>
LPO VD1 PWRUP_1V8 VSS PWRUP_N_1V8
```

Four ideal voltage loads hold outputs 0–3 at 0.5, 0.6, 0.7, and 0.8 V.
Their branch currents are the delivered output currents. Positive active power
is `-VDD * i(VDD)`. The loop ports are shorted through an ideal 0 V source for
DC and transient analysis. Both supply and enable return to the VSS boundary;
there are no assumptions about the participant's internal instance names.

| Deck | Measurement |
| --- | --- |
| `dc.spice` | Four output currents, CTAT voltage VD1, and active supply power at one process/temperature/supply point |
| `tran.spice` | Startup after enable, sustained settling of all four currents and VD1, active tail means, and shutdown supply current |
| `stability.spice` | Two-injection Tian loop return ratio from 1 Hz through 1 GHz; phase margin at every descending unity-magnitude crossing |

Default transient stimulus: supply ramps in 10 ns; enable rises at 1 us over
1 ns; shutdown begins at 10 us over 1 ns; simulation ends at 12 us, with at most
2 ns between samples. Settling means the first sampled point after the **last**
violation of a ±1% band around each output's DC operating point, sustained until
shutdown, with at least 1 us remaining. It is not merely the first crossing of a
threshold. If the transient bench runs alone, its final active 1 us average
supplies the targets. This self-referenced development result is identified in
JSON. The complete evaluation runs DC first and uses the DC targets. Missing
startup, insufficient observation time, and nonfinite results fail the check.

Shutdown current is the mean `-i(VDD)` over the last 1 us; output compliance
loads remain connected. This explicitly measures the submitted circuit under
the stated powered-down loads, not an unloaded leakage abstraction.

The loop probe preserves DC connectivity and makes separate voltage/current AC
injections. The algebra follows the original project's Tian probe, based on
Michael Tian et al., “Striving for Small-Signal Stability,” IEEE Circuits and
Devices Magazine, January 2001. With this return-ratio sign convention the
low-frequency phase is +180 degrees, so phase at unity magnitude is directly
the phase margin. The evaluator linearly interpolates gain and unwrapped phase
in log frequency. It reports the smallest phase margin among descending unity
crossings; absence of a crossing fails. This conventional single-loop metric
and startup test are useful checks, not a general proof of multi-loop stability.

The configured corner grid selects the installed PDK's `sky130.lib.spice`
sections `tt`, `ss`, `ff`, `sf`, and `fs`. Those sections include their own device
corner files but hold resistor and capacitor process variation at **typical**.
Thus a “45-case corner grid” means 5 library sections × 3 temperatures × 3
supplies; it is not exhaustive independent MOS/BJT/resistor/capacitor variation.
Monte Carlo, mismatch, thermal gradients, and voltage-compliance sweeps beyond
the four fixed loads are outside this initial contract. The clean schematic and
extracted design always receive identical model sections and stimuli.
