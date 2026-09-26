# Reference qualification and timings

Measured 2026-09-26 on this device. **All 45 schematic conditions and all 45
RC conditions passed DC, startup/shutdown, and stability analysis.** DRC has
zero violations; both direct LVS and the contracted-RC connectivity comparison
match uniquely. The reference passes the finalized electrical gates and scores
**57.420** on the published RC corner profile.

This qualifies the declared bandgap evaluation grid, not the entire temperature
sensor or every possible process variation. The restored original full-sensor
flow was checked separately; see [dependency-resolution.md](dependency-resolution.md).

## Electrical baseline

Nominal condition: tt, 27 C, 1.8 V. Four output loads are held at 0.5, 0.6,
0.7 and 0.8 V respectively. The baseline is the fully schematic amplifier and
bandgap, avoiding the original bench's mixed schematic/extracted OTA definition.

| Metric | Schematic | Distributed RC |
| --- | ---: | ---: |
| Output 0 current (uA) | 1.18563 | 1.1521 |
| Output 1 current (uA) | 1.18542 | 1.15191 |
| Output 2 current (uA) | 1.18521 | 1.15171 |
| Output 3 current (uA) | 1.18498 | 1.1515 |
| VD1 (V) | 0.738867 | 0.738317 |
| Settling (us) | 0.434788 | 0.64832 |
| Shutdown current (nA) | 3.74177 | 4.36147 |
| Active power (uW) | 74.2328 | 72.7987 |
| Phase margin (degrees) | 59.5406 | 59.9204 |
| Unity-gain frequency (MHz) | 6.38091 | 4.92811 |

The complete 45-condition ranges follow. The [90-row CSV](reference-results.csv)
retains every condition's four currents and individual measurements, with units
named in the column headers.

| Metric | Schematic range | RC range |
| --- | ---: | ---: |
| All output currents (uA) | 0.930698 to 1.49219 | 0.905835 to 1.45026 |
| VD1 (V) | 0.565826 to 0.84756 | 0.565109 to 0.847152 |
| Settling (us) | 0.293314 to 0.848994 | 0.380525 to 0.936969 |
| Shutdown current (nA) | 2.68443 to 156.389 | 3.03601 to 157.068 |
| Active power (uW) | 34.6459 to 124.644 | 33.8348 to 122.803 |
| Phase margin (degrees) | 46.8171 to 78.2898 | 47.2013 to 78.2183 |
| Unity-gain frequency (MHz) | 2.3655 to 8.8736 | 1.82723 to 6.91794 |

Measured paint area: **10467.146732 um²**, approximately
98.32 × 106.46 um. The reference export contains 228 designed device instances,
6,746 numeric wiring resistors and 2,129 numeric wiring capacitors.

## Scoring and finalized gates

The [evaluation contract](evaluation.md) gives the exact formula. On this grid:

- Worst normalized transfer deviation D: **0.603976**.
- Worst current deviation: **3.0199%**, output 0, fs, -40 C, 1.9 V.
- Worst VD1 difference: **0.746559 mV**, fs, 125 C, 1.9 V.
- Settling penalty ratio: **1.62833**.
- Active-power penalty ratio: **1**.
- Reference area ratio: 1; resulting score: **57.419990**.

Retained the source's 45-degree phase-margin minimum and 2 us settling maximum,
which both views satisfy across this grid. These replace the 40-degree/5 us
provisional exploration values. Current/voltage sanity gates are 0.4–2.5 uA
per output and 0.45–1.05 V at VD1; active power is limited to 300 uW and shutdown
current to 1 uA. These broad gates establish functionality; matched-condition
transfer, settling and power penalties provide the ranking pressure. A 100 nA
leakage limit would reject the unchanged schematic at hot/fast conditions.
The 5% current and 10 mV voltage values are scoring scales, not hard gates.
All numerical rules are in [competition.yaml](../competition.yaml).

## Observed runtimes

Apple M5, 24 GiB RAM, macOS arm64. Python 3.14.3,
Magic 8.3.541, Netgen 1.5.323 and ngspice 47 with KLU. Four corner cases run in
parallel; each simulator uses one thread. The portable typical test overlapped
part of the corner run, so these are observed costs, not isolated benchmarks.
Times are seconds within each stage; initialization/hashing and command startup
add overhead. Simulator model loading dominates the short physical checks.

| Check | Copied-project typical profile | 45-condition corner profile |
| --- | ---: | ---: |
| doctor | 12.897 | 9.541 |
| drc | 0.663 | 0.561 |
| lvs | 0.868 | 0.912 |
| area | 0.141 | 0.145 |
| extract | 0.355 | 0.396 |
| Simulate schematic: DC + transient + stability | 32.326 | 425.847 |
| Simulate layout: DC + transient + stability | 63.615 | 778.052 |
| Score | 0.031 | 0.048 |
| Sum of stage times | 110.896 | 1215.502 |

Allow roughly 1.8 minutes for the full typical flow and
20.3 minutes for the two-view corner flow on this machine.
An individual analysis or physical check can be run separately while iterating.
The focused [acceptance suite](acceptance.md) passed all 16 checks in 5.73 s;
it includes real DRC and LVS failures, not only successful reference runs.

## Reproduction and provenance

From a configured project directory:

```sh
uv run bandgap all --profile corners --out runs/qualification
uv run bandgap score --profile corners --out runs/qualification
```

The first run measured with provisional scoring values. The second rescored the
same unchanged measurements after freezing the final gates and qualification
flag; scoring-only changes do not invalidate measured circuit results.
The independent copied-project typical run used a fresh virtual environment
with only PyYAML installed, an empty PYTHONPATH and PATH=/usr/bin:/bin. Absolute
EDA tool paths and the installed PDK were supplied through local YAML. No CIC
package or parent-repository file was needed. Both schematic views regenerated
byte-identically there; flat custom-track physical checks also passed.

PDK fingerprint (technology, models and Netgen setup):
`88b86438b9066df1e183f0498368e1e354ea38ac2f0b0afec0da99aaa919c4db`.

Measurement/input signature:
`23958be7481ee7a581b93d45e616f1188a9ff23fc17f929fa28175c5d9f71196`.

Final competition.yaml SHA-256:
`e9117fe10ca69a021348a8fb6154d2acbc921333d4ffe3d9d2cd9e9ba160bbf4`.

CSV SHA-256:
`a70c6844e8efc7368c14cb9c747e4827df7dbd80bbd228c36d6beea032bf368f`.

Historical raw decks, tables, extraction files and logs remain in the original
aicex extraction workspace, outside this standalone repository. JSON reports
there bind those artifacts to the input signature. The CSV and this summary
are the compact maintained baseline; rerunning the commands above creates fresh
artifacts in this checkout's ignored `runs/qualification` directory.
Imported view revisions/hashes are in [cells/manifest.json](../cells/manifest.json).

## Limits of this qualification

The grid uses tt/ss/ff/sf/fs library sections, -40/27/125 C and 1.7/1.8/1.9 V.
These library sections use typical resistor/capacitor models; independent passive
extremes, mismatch, noise, PSRR, thermal gradients and continuous sweeps are not
qualified. Magic `drc(full)` is the required DRC deck; KLayout and antenna
signoff are outside this release.

RC is the thresholded Magic extresist model, not a complete field-solver result.
The retained dummy-terminal and small-viali extraction warnings, the resistance
cross-check, and contact/substrate/model limitations are documented in
[RC validation](rc-validation.md). Connectivity matches and passing simulations
do not remove those limits. Competition organizers should use the published
evaluator/configuration and consistent tool/PDK versions across entries.
