# Circuit to lay out

The circuit is Carsten Wulff's `LELOTEMP_BIAS_IBP` from the temperature sensor
`lelo_temp_sky130a`. Source revisions and individual imported-file hashes are
in [the manifest](../cells/manifest.json). The complete temperature sensor's
oscillator and digital counter are outside this competition.

The bandgap core compares bipolar junctions with differing current densities.
The source design combines a factor-eight device ratio and factor-eight
current ratio. Their voltage difference is approximately

$$
\Delta V_{BE} = \frac{kT}{q}\ln(64),\qquad
I_R = \frac{\Delta V_{BE}}{R_\mathrm{series}}
$$

Here temperature is in kelvin and `R_series` is the full resistor ladder.
The amplifier `LELOTEMP_OTAR` closes the loop and drives the current-source
PMOS gates. The mirrored output currents rise with temperature. The junction
voltage exposed at `VD1` falls with temperature. In the original sensor these
quantities establish an oscillator frequency; the standalone evaluator observes
the bandgap's current, voltage, startup and stability directly.

The design includes startup circuitry, cascode bias generation, compensation
capacitors, power gating and explicit rail-tied filler devices. Preserve these
devices and their schematic connections. Their presence in the fixed netlist
is intentional; extraction has not redesigned or removed them.

## Boundary

The canonical netlist order is:

```spice
.subckt LELOTEMP_BIAS_IBP VDD_1V8 LPI IBP_1U<3> IBP_1U<2> IBP_1U<1> IBP_1U<0> LPO VD1 PWRUP_1V8 VSS PWRUP_N_1V8
```

| Port | Meaning/test condition |
| --- | --- |
| `VDD_1V8`, `VSS` | Positive supply and ground |
| `PWRUP_1V8` | High enables operation |
| `PWRUP_N_1V8` | Complementary enable, driven low during operation |
| `IBP_1U<0:3>` | Four PTAT current outputs; evaluation clamps them respectively at 0.5, 0.6, 0.7 and 0.8 V |
| `VD1` | CTAT junction-voltage output, measured with the simulator's ideal voltage probe |
| `LPO`, `LPI` | Amplifier/feedback loop access; joined through a zero-volt source during DC/transient and a two-injection probe during stability analysis |

Port labels must be electrically meaningful and accessible to parent wiring.
DRC/LVS checks electrical/geometry rules, but does not establish practical
top-level pin accessibility or all analog placement practices. Review these
as part of a submitted design's engineering explanation.

The supplied Xschem hierarchy remains editable. Two generated SPICE views have
the same topology: `bandgap.spice` retains schematic diffusion parameters for
simulation, while `bandgap.lvs.spice` uses the source's LVS netlisting mode.
Both include a fully schematic amplifier. The original bench's mixed
schematic/extracted amplifier definition is explained in
[RC validation](rc-validation.md).

The supplied reference is a baseline and an example of hierarchical assembly.
Preserving matching, symmetry, guard/tap placement and sensible routing is good
engineering, although ordinary extracted RC does not model every benefit of
those practices. The measured score must be interpreted within those limits.
