#!/usr/bin/env python3
"""Physical/consumer acceptance checks using disposable copies and real EDA tools.

No DUT simulation or CIC utility is needed. Successful scratch trees are removed;
failures retain logs. Pass --keep to inspect all generated artifacts.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check
import physical
import simulation


def rejects(name, callback, contains):
    try:
        callback()
    except RuntimeError as exc:
        if contains not in str(exc):
            raise AssertionError(f"{name}: unexpected rejection: {exc}") from exc
    else:
        raise AssertionError(f"{name}: invalid input was accepted")
    print(f"PASS {name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    local = check.local_config()
    scratch = Path(tempfile.mkdtemp(prefix="bandgap-acceptance-"))
    started = time.monotonic()

    def project(name):
        dest = scratch / name
        shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns("runs", "__pycache__", "tools.local.yaml", ".venv", ".git", "site", ".docs-build", "*.egg-info", "pdk", "submissions"))
        # Resolved paths also support workstations configured without PDK_ROOT.
        (dest / "tools.local.yaml").write_text(json.dumps(local))
        return dest

    def top(p):
        return p / "reference/LELO_TEMP_SKY130A/LELOTEMP_BIAS_IBP.mag"

    def invoke(p, command, expected=None):
        run = subprocess.run([sys.executable, str(p / "tools/check.py"), command,
                              "--mode", "c", "--out", str(p / "runs/result")],
                             cwd=scratch, text=True, capture_output=True, timeout=60)
        output = run.stdout + run.stderr
        (p / f"acceptance-{command}.log").write_text(output)
        if expected is None:
            if run.returncode:
                raise AssertionError(output)
        elif not run.returncode or expected not in output:
            raise AssertionError(f"Expected rejection containing {expected!r}: {output}")
        print(f"PASS {p.name}/{command}", flush=True)

    try:
        baseline = project("portable-reference")
        for command in ("drc", "lvs", "area"):
            invoke(baseline, command)
        base_area = json.loads((baseline / "runs/result/area.json").read_text())["area_um2"]
        if not base_area > 0:
            raise AssertionError("Reference area must be positive")

        missing = project("missing-child")
        t = top(missing)
        t.write_text(t.read_text().replace("use LELOTEMP_BIAS_IBP_BIP ", "use ABSENT_CHILD "))
        invoke(missing, "drc", "Missing or ambiguous child")

        ambiguous = project("ambiguous-child")
        cell = top(ambiguous).parent / "LELOTEMP_BIAS_IBP_P_SRC.mag"
        cell.write_text(cell.read_text().replace(
            "use REYATR_PCH_4C5F0 xca2 ../../cells/REY_ATR_SKY130A", "use REYATR_PCH_4C5F0 xca2"))
        shutil.copyfile(ambiguous / "cells/REY_ATR_SKY130A/REYATR_PCH_4C5F0.mag",
                        cell.parent / "REYATR_PCH_4C5F0.mag")
        invoke(ambiguous, "drc", "Missing or ambiguous child")

        escape = project("external-child")
        outside = scratch / "external-cell"
        outside.mkdir()
        source = top(escape).parent / "LELOTEMP_BIAS_IBP_BIP.mag"
        shutil.copyfile(source, outside / source.name)
        t = top(escape)
        t.write_text(t.read_text().replace("use LELOTEMP_BIAS_IBP_BIP xbip",
                                           f"use LELOTEMP_BIAS_IBP_BIP xbip {outside}"))
        invoke(escape, "drc", "escapes the project/submission")

        modified = project("modified-fixed-tile")
        tile = modified / "cells/REY_ATR_SKY130A/REYATR_PCH_4C5F0.mag"
        tile.write_text(tile.read_text() + "\n")
        invoke(modified, "drc", "Provided tile was modified")

        violation = project("drc-violation")
        t = top(violation)
        t.write_text(t.read_text().replace("<< labels >>",
                     "<< metal1 >>\nrect -10000 -10000 -9999 -9900\n<< labels >>"))
        invoke(violation, "drc", "DRC violations")

        short = project("shorted-outputs")
        t = top(short)
        t.write_text(t.read_text().replace("<< labels >>",
                     "<< metal4 >>\nrect 3686 21200 4466 21260\n<< labels >>"))
        invoke(short, "lvs", "LVS failed")

        bbox = project("spoofed-bounds")
        t = top(bbox)
        t.write_text(t.read_text().replace("<< properties >>", "<< properties >>\nstring FIXED_BBOX 0 0 1 1"))
        invoke(bbox, "area")
        area = json.loads((bbox / "runs/result/area.json").read_text())["area_um2"]
        if area != base_area:
            raise AssertionError("Editable FIXED_BBOX changed the reported physical area")

        # Device dimensions must fail LVS even when connectivity is identical.
        report = json.loads((baseline / "runs/result/lvs.json").read_text())
        raw = Path(report["netlist"]).read_text()
        if "w=1.6" not in raw:
            raise AssertionError("Reference fixture no longer contains the expected transistor")
        wrong = scratch / "wrong-width.spice"
        wrong.write_text(raw.replace("w=1.6", "w=3.2", 1))
        compare = scratch / "property-compare"
        compare.mkdir()
        rejects("LVS device dimension mismatch", lambda: physical.lvs(
            local, wrong, baseline / "schematic/bandgap.lvs.spice", "LELOTEMP_BIAS_IBP", compare), "LVS failed")
        wrong.write_text(raw.replace("sky130_fd_pr__nfet_01v8", "undefined_device", 1))
        rejects("LVS unresolved device", lambda: physical.lvs(
            local, wrong, baseline / "schematic/bandgap.lvs.spice", "LELOTEMP_BIAS_IBP", compare), "Unresolved or empty")

        # Exercise report consumers without running doctor or full simulations.
        check.ROOT = baseline
        options = SimpleNamespace(layout=None, out=baseline / "runs/result", track="provided", mode="c")
        check.Evaluation(options).previous("area")
        t = top(baseline)
        original = t.read_text()
        t.write_text(original + "\n")
        rejects("stale layout report", lambda: check.Evaluation(options).previous("area"), "stale")
        t.write_text(original)
        area_report = json.loads((baseline / "runs/result/area.json").read_text())
        artifact = Path(area_report["directory"]) / "area.mag"
        artifact.write_text(artifact.read_text() + "\n")
        rejects("modified retained artifact", lambda: check.Evaluation(options).previous("area"), "changed or disappeared")

        # LVS must accept electrical finger partitioning, but not a resized device
        # that merely preserves W/L. These use the official comparison function/setup.
        fingers = scratch / "fingers"
        fingers.mkdir()
        one, split, resized = [fingers / name for name in ("one.spice", "split.spice", "resized.spice")]
        header = ".subckt finger_test d g s b\n"
        end = ".ends finger_test\n"
        model = "sky130_fd_pr__nfet_01v8"
        one.write_text(header + f"X1 d g s b {model} w=2 l=0.5\n" + end)
        split.write_text(header + f"X1 d g s b {model} w=1 l=0.5\nX2 d g s b {model} w=1 l=0.5\n" + end)
        resized.write_text(header + f"X1 d g s b {model} w=4 l=1\n" + end)
        for name in ("equivalent", "resized"):
            (fingers / name).mkdir()
        physical.lvs(local, split, one, "finger_test", fingers / "equivalent")
        print("PASS equivalent parallel transistor fingers", flush=True)
        rejects("same W/L with changed dimensions", lambda: physical.lvs(
            local, resized, one, "finger_test", fingers / "resized"), "LVS failed")

        table = scratch / "nonfinite.dat"
        table.write_text("time value\n0 nan\n")
        rejects("nonfinite simulation output", lambda: simulation.read_table(table, 2), "nonfinite")
        trace = [[0.0] * 7, [1e-9] + [0.0] * 6, [2e-9] + [0.0] * 6]
        rejects("truncated transient", lambda: simulation.measure_tran(trace, simulation.DEFAULTS, 1.8), "ended before")
    except Exception:
        print(f"FAIL: retained acceptance artifacts at {scratch}", file=sys.stderr)
        raise
    else:
        print(f"All acceptance checks passed in {time.monotonic()-started:.2f}s.")
        if args.keep:
            print(f"Artifacts: {scratch}")
        else:
            shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
