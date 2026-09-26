# Evaluator acceptance checks

2026-09-26. These checks follow the portable-project and failure-behavior
requirements in [extraction-plan.md](extraction-plan.md). They test real invalid
submissions and incomplete outputs, including the missing-cell false-pass
scenario that originally blocked the source flow. They do not substitute for
the analog/RC/corner qualification recorded separately.

Run from a competition-folder copy, with installed Magic, Netgen, Python/PyYAML,
and configured Sky130A paths:

```sh
uv run bandgap acceptance
# Preserve successful scratch directories and tool logs for inspection:
uv run bandgap acceptance --keep
```

The script uses `sys.executable` for child Python commands, resolves local tool
and PDK configuration, and makes disposable project copies outside the source
folder. Those copies contain ordinary files and the same evaluator that a
participant receives. Every physical check calls `tools/check.py` as a separate
process. CIC is not imported or invoked. Full analog simulations and doctor
model smoke tests are omitted to keep this focused suite quick.

## Fresh observed results

All 16 checks passed in **5.42 seconds** on the current machine. This is one
observed run, not a runtime guarantee.

| Check | Deliberate condition | Verified behavior |
| --- | --- | --- |
| Portable reference DRC | Unmodified project copy outside aicex | Zero violations |
| Portable reference LVS | Fresh extraction in that copy | Unique circuit match |
| Portable reference area | Full flattened physical geometry | Positive area, approximately 10467.146732 µm² |
| Missing child | Replace one top-level child name with a nonexistent cell | Rejected before Magic runs |
| Ambiguous child | Two reachable files define the same implicit child name | Rejected before Magic runs |
| External child | Explicit child path points outside project/submission directories | Rejected before Magic runs |
| Modified fixed tile | Change a supplied immutable tile file | Provided-cell track rejects it |
| DRC violation | Add a 0.005 µm-wide metal1 rectangle far outside the original bounds | Fails with two reported DRC violations |
| Physical output short | Add metal4 shorting the four current-output routes | LVS rejects the layout |
| Spoofed area bounds | Set the top `FIXED_BBOX` property to 0,0,1,1 | Measured physical area remains exactly unchanged |
| Device dimension mismatch | Double one extracted transistor finger width without changing connectivity | LVS rejects the property mismatch |
| Unresolved electrical device | Replace one extracted model name with an undefined name | Rejected before a Netgen match could be accepted |
| Stale input report | Change layout bytes after a passing area report | Report consumer rejects the old signature |
| Modified retained artifact | Change the saved flattened layout after a passing area report | Report consumer rejects the changed artifact hash |
| Nonfinite simulation output | Supply a table containing NaN | Measurement parser rejects it |
| Truncated transient | Supply an otherwise ordered trace that stops before the stimulus completes | Transient measurement rejects it |

The circuit-short and width-mismatch cases establish both connectivity and
property failure handling. The modified bounds case exercises area measurement
without trusting participant-editable display/placement properties. The
simulation cases exercise the public measurement consumer functions against
invalid data; they do not rerun the circuit or assert a duplicated implementation
formula.

With `--keep`, the run records subprocess output in
`acceptance-<command>.log` within each copied project, and the evaluator retains
its normal detailed run directories. The observed run's full scratch tree was:

```text
/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-acceptance-whwug7bd
```

An earlier manual copied-folder spike additionally ran the actual `score`
command after (a) changing layout bytes and (b) modifying a retained doctor
model deck. Both attempts were rejected before scoring. Each doctor model
probe took approximately 9–10 seconds; the maintained acceptance suite checks
the same report-consumer behavior using area artifacts without simulation.

## Review findings addressed

The accompanying implementation review identified and addressed three
provenance/boundary gaps: explicit child paths could leave the project, the
sourced Magic `.magicrc` was absent from the PDK fingerprint, and the immutable
cell manifest was absent from the report signature. The current evaluator
bounds hierarchy resolution and fingerprints both files.

The reviewer also checked report lifecycle handling: a callback's failed status
must remain failed, and a wrapper must not hash a callback's `result.json` and
then overwrite the same file, invalidating its own artifact digest. The current
wrapper preserves failure and excludes its own root result file while retaining
hashes of actual generated decks, data, logs, and nested case results.

Scoring requires all three declared analyses, complete selected corner coverage,
finite measurements, and unchanged prerequisite artifacts. Scoring limits are
recorded in the score report separately from the measurement signature, so
freezing transparent weights does not require rerunning identical simulations.

These are practical evaluation checks, not a server security boundary. The
protected submission service remains outside this project. The custom-device
track's originality requirement also cannot be proven by DRC or LVS alone.

## Integrated portability and custom-track checks

After integration, a complete typical-profile run passed from a copied project
in a fresh virtual environment containing only the declared PyYAML dependency.
`PATH` was `/usr/bin:/bin`, `PYTHONPATH` was empty, and the EDA binaries and PDK
were configured with absolute paths. Both schematic netlists regenerated
byte-identically there. This exercises doctor, DRC, LVS, area, full RC export,
all three analyses in both views, and scoring without installed CIC Python
packages or CIC commands on PATH. See [reference-results.md](reference-results.md)
for numerical results and timings.

The copied project also passed capacitance-only extraction (0.44 s) followed
by an independent layout DC analysis (17.11 s while the RC grid was running),
covering the faster `--mode c` and `--analysis dc` development paths.

An additional flat version of the reference passed `--track custom` DRC, LVS
and RC extraction in 0.45, 0.31 and 0.41 seconds respectively. This checks that
the alternate physical representation works; it does not make a flattened
reference an original competition entry. Scratch files are retained locally in
`/var/folders/w1/1x9cdy092l9331ys__k74djm0000gn/T/bandgap-custom-track-c2dkrita`.
