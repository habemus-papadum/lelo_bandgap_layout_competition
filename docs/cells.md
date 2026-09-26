# Reusable cells and circuit interface

The package includes the complete local reference hierarchy: 22 circuit Magic
cells in `reference/LELO_TEMP_SKY130A`, 23 reusable Magic tiles in
`cells/REY_ATR_SKY130A`, and the matching editable schematic/symbol views.
The bipolar primitive geometry comes from the configured Sky130A PDK, which
defaults to the complete installation bundled in `pdk/`.
There are no source-repository symlinks and no generators to install.

## Bandgap interface

The canonical simulation and LVS subcircuits use this same positional order:

```spice
.subckt LELOTEMP_BIAS_IBP VDD_1V8 LPI IBP_1U<3> IBP_1U<2> IBP_1U<1> IBP_1U<0> LPO VD1 PWRUP_1V8 VSS PWRUP_N_1V8
```

| Pins | Purpose |
| --- | --- |
| `VDD_1V8`, `VSS` | Analog supply and ground; source design uses 1.7–1.9 V |
| `PWRUP_1V8`, `PWRUP_N_1V8` | Complementary enable inputs; active when high/low respectively |
| `IBP_1U<3:0>` | Four sourced PTAT current outputs; nominal order of magnitude 1 µA each |
| `VD1` | CTAT bipolar-emitter voltage output; externally observe without drawing significant current |
| `LPI`, `LPO` | Loop input and amplifier output; connect through a zero-volt source for ordinary operation, insert the documented probe for loop analysis |

Individual SPICE bus nodes use angle brackets, such as `IBP_1U<0>`. Xschem source
bus labels still use its normal `[]` syntax; `schematic/xschemrc` consistently
exports angle brackets. Circuit use must not leave the loop disconnected.

The editable logical hierarchy is `LELOTEMP_BIAS_IBP` → `LELOTEMP_OTAR` and
`LELOTEMP_BIPOLAR`, plus REY_ATR tiles. The Magic hierarchy divides the same
circuit into placement/routing groups, so logical and physical instance names
need not be identical. The complete OTA and bandgap layouts are assembly
examples, not indivisible predefined tiles.

## Device and passive tiles

Each row below has `.mag`, `.sch`, and `.sym` views under
`cells/REY_ATR_SKY130A`. MOS dimensions are the SPICE parameters in µm: `W` is the
model instance width and `nf=2` specifies two fingers. Use the actual supplied
netlist/model convention when checking effective device widths.

| Cell name, without `REYATR_` prefix | Device and parameters | Schematic pin order |
| --- | --- | --- |
| `PCH_2C5F0`, `PCH_2C5F0D` | `sky130_fd_pr__pfet_01v8`, W=1.92, L=0.94, nf=2 | D G S B |
| `PCH_4C5F0`, `PCH_4C5F0D` | `sky130_fd_pr__pfet_01v8`, W=3.2, L=0.94, nf=2 | D G S B |
| `PCH_4C1F2`, `PCH_4C1F2D` | `sky130_fd_pr__pfet_01v8`, W=3.2, L=0.22, nf=2 | D G S B |
| `PCH_11C5F0`, `PCH_11C5F0D` | `sky130_fd_pr__pfet_01v8`, W=7.68, L=0.94, nf=2 | D G S B |
| `LVT_PCH_11C5F0` | `sky130_fd_pr__pfet_01v8_lvt`, W=7.68, L=0.94, nf=2 | D G S B |
| `NCH_4C5F0`, `NCH_4C5F0D` | `sky130_fd_pr__nfet_01v8`, W=3.2, L=0.94, nf=2 | D G S B |
| `CAPX1` | `sky130_fd_pr__cap_mim_m3_1`, W=4.8, L=5 | A B; primitive terminals connect B A |
| `RES_36C2F0` | Two series `sky130_fd_pr__res_high_po`, each W=0.4, L=8.16 | N P B |

The five `D` suffix variants **short drain and gate inside the Magic tile**.
Their upstream schematic/symbol views still have four independent terminals;
connect D and G to the same net explicitly when using these views. The canonical
bandgap does this using ordinary symbols and explicit connections. Instantiating
a `D` variant between independent D/G nets creates a real short.

`cells/tiles.spice` supplies the 13 electrical tile definitions, including those
five variants, for participants' separate experiments. Load the Sky130 models in
your bench. Do not include it alongside `schematic/bandgap.spice`, which already
contains all tile definitions needed by the complete DUT.

## Tap tiles

These ten additional physical tiles have no independent SPICE device:

- `REYATR_PCH_2CTAPBOT`, `REYATR_PCH_2CTAPTOP`
- `REYATR_PCH_4CTAPBOT`, `REYATR_PCH_4CTAPTOP`
- `REYATR_PCH_11CTAPBOT`, `REYATR_PCH_11CTAPTOP`
- `REYATR_NCH_4CTAPBOT`, `REYATR_NCH_4CTAPTOP`
- `REYATR_RES_36CTAPBOT`, `REYATR_RES_36CTAPTOP`

Their `.sch` and `.sym` views are intentionally empty upstream views: the cells
supply well/substrate geometry and bulk connections, not modeled components.
The reference uses the matching top/bottom tiles around device stacks; study
those assemblies before rearranging tiles. An empty logical view does not make
physical taps optional. Connect PMOS bulk to `VDD_1V8`, and NMOS/resistor substrate
to `VSS`, preserving the supplied circuit's bulk connectivity.

All transistor tiles have nominal `FIXED_BBOX` 8 × 4 µm; `CAPX1` is 8 × 8 µm and
`RES_36C2F0` is 16 × 4 µm. Tap nominal heights are 2.4 µm, with widths 8 µm for
MOS taps and 16 µm for resistor taps. These are **placement bounds**, not physical
area estimates: wells, diffusion, or routing can extend beyond them. Area judging
must include actual geometry. The verified Magic scale is 0.005 µm per file unit.

Preserve the tile grid and use legal rotations/reflections; inspect ports after
transformation. Interconnect may be added in parent assembly cells. DRC and LVS
remain necessary after abutting tiles: a previously passing tile does not make
arbitrary abutment or bulk connectivity valid. The reference is an example of
stack/tap use, not a substitute for those checks.

## Bipolar primitive and fillers

`LELOTEMP_BIPOLAR` contains one emitter on `VD1` and eight parallel emitters on
`VD2`; all bases and collectors connect to `VSS`. Schematic device model:
`sky130_fd_pr__pnp_05v5_W3p40L3p40`. Magic primitive cell:
`sky130_fd_pr__rf_pnp_05v5_W3p40L3p40`, resolved from the configured PDK.
The reference adds substrate contacts around this assembly.

All explicitly modeled dummy/filler transistors remain in the canonical
schematic: the five `xcc` PMOS devices, eleven `xfill_p_su` devices, eight
`xfill_p_cc` devices, and the OTA's two PMOS plus one NMOS fillers. They are
rail-tied devices, not comments or omitted geometry. The supplied-cell track
fixes the 23 Magic tile files listed in `cells/manifest.json` (`immutable_magic`);
the custom-device track allows alternate geometry for the same prescribed
circuit. Neither track changes circuit sizes or connectivity. See the competition
rules for the evaluator's exact track enforcement.
