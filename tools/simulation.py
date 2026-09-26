"""Run readable ngspice benches and measure only the public DUT ports.

No waveform-package dependency: ngspice writes named, real-valued columns.
Every generated deck, numerical table and simulator log is retained.
"""
from __future__ import annotations

import concurrent.futures
import itertools
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

ANALYSES = ("dc", "tran", "stability")
DEFAULTS = {
    "enable_s": 1e-6,
    "edge_s": 1e-9,
    "off_s": 10e-6,
    "stop_s": 12e-6,
    "step_s": 2e-9,
    "settling_fraction": 0.01,
    "hold_s": 1e-6,
    "jobs": 4,
}


def read_table(path: Path, width: int) -> list[list[float]]:
    """Fail closed on missing, malformed, empty, or nonfinite output."""
    if not path.is_file():
        raise RuntimeError(f"ngspice did not write {path.name}; inspect ngspice.log")
    lines = path.read_text().splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"Empty measurement table: {path}")
    data = []
    for line in lines[1:]:
        try:
            row = [float(value) for value in line.split()]
        except ValueError as exc:
            raise RuntimeError(f"Malformed measurement row in {path}") from exc
        if len(row) != width or not all(math.isfinite(value) for value in row):
            raise RuntimeError(f"Invalid or nonfinite measurement row in {path}")
        data.append(row)
    return data


def measure_dc(data: list[list[float]], supply: float) -> dict:
    if len(data) != 1:
        raise RuntimeError("DC bench must produce exactly one operating point")
    row = data[0]
    return {"currents_a": row[1:5], "voltage_v": row[5],
            "power_w": -row[6] * supply, "supply_current_a": -row[6]}


def measure_tran(data: list[list[float]], settings: dict, supply: float,
                 target: list[float] | None = None) -> dict:
    enable = settings["enable_s"] + settings["edge_s"]
    off, stop, hold = (settings[key] for key in ("off_s", "stop_s", "hold_s"))
    if len(data) < 3 or any(b[0] <= a[0] for a, b in zip(data, data[1:])):
        raise RuntimeError("Transient time values are absent or not increasing")
    if data[0][0] > settings["step_s"] or data[-1][0] < stop * (1 - 1e-6):
        raise RuntimeError("Transient ended before the complete stimulus was measured")
    active = [row for row in data if off - hold <= row[0] < off]
    disabled = [row for row in data if stop - hold <= row[0] <= stop]
    if len(active) < 2 or len(disabled) < 2:
        raise RuntimeError("Missing sustained active or shutdown observation interval")
    final = [statistics.fmean(row[k] for row in active) for k in range(1, 7)]
    target = final[:5] if target is None else target
    if any(value <= 1e-9 for value in target[:4]) or target[4] <= 0.1:
        raise RuntimeError("No valid active current/voltage to define startup settling")
    active_trace = [row for row in data if enable <= row[0] < off]
    tolerances = [abs(value) * settings["settling_fraction"] for value in target]
    last_outside = -1
    for i, row in enumerate(active_trace):
        if any(abs(row[k + 1] - target[k]) > tolerances[k] for k in range(5)):
            last_outside = i
    first_inside = last_outside + 1
    if first_inside >= len(active_trace):
        raise RuntimeError("Outputs never settle inside the specified band")
    settled_at = active_trace[first_inside][0]
    if off - settled_at < hold:
        raise RuntimeError("Outputs did not remain settled for the required hold interval")
    return {
        "currents_a": final[:4], "voltage_v": final[4],
        "power_w": -final[5] * supply,
        "settling_s": settled_at - enable,
        "leakage_a": -statistics.fmean(row[6] for row in disabled),
        "settling_target": "DC operating point" if target != final[:5] else "active tail mean",
        "settling_fraction": settings["settling_fraction"],
        "hold_s": hold,
    }


def measure_stability(data: list[list[float]]) -> dict:
    if len(data) < 3 or data[0][0] > 1.01 or data[-1][0] < 0.999e9:
        raise RuntimeError("Loop sweep did not cover 1 Hz through 1 GHz")
    if any(b[0] <= a[0] for a, b in zip(data, data[1:])):
        raise RuntimeError("Loop sweep frequencies are not increasing")
    # The Tian return ratio has low-frequency phase +180 degrees. Its phase
    # at unity magnitude is directly the phase margin (not phase + 180).
    phase_offset = 360 * round((180 - data[0][2]) / 360)
    if not 90 < data[0][2] + phase_offset < 270 or data[0][1] <= 0:
        raise RuntimeError("No expected negative-feedback operating point at low frequency")
    crosses = []
    for a, b in zip(data, data[1:]):
        if a[1] > 0 >= b[1]:
            fraction = a[1] / (a[1] - b[1])
            frequency = math.exp(math.log(a[0]) + fraction * math.log(b[0] / a[0]))
            phase = a[2] + fraction * (b[2] - a[2]) + phase_offset
            crosses.append({"frequency_hz": frequency, "phase_margin_deg": phase})
    if not crosses:
        raise RuntimeError("No descending unity-gain crossing within loop sweep")
    return {"phase_margin_deg": min(x["phase_margin_deg"] for x in crosses),
            "unity_gain_hz": crosses[0]["frequency_hz"],
            "low_frequency_gain_db": data[0][1], "unity_crossings": crosses}


def run_simulation(project: Path, config: dict, tool_config: dict, dut: Path,
                   view: str, profile: str, outdir: Path,
                   analyses: list[str] | None = None) -> dict:
    """Evaluate a fixed corner grid. Invalid runs return status='fail' with logs.

    Independent cases may run concurrently; each ngspice process uses one
    thread. Individual analyses are selectable for development. Only a result
    containing all three analyses can satisfy the complete scoring contract.
    """
    started = time.monotonic()
    project, dut, outdir = Path(project).resolve(), Path(dut).resolve(), Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    selected = list(ANALYSES) if analyses is None else list(analyses)
    if not selected or any(name not in ANALYSES for name in selected):
        raise ValueError(f"Choose analyses from {ANALYSES}")
    selected = [name for name in ANALYSES if name in selected]
    settings = {**DEFAULTS, **config.get("simulation", {})}
    if not (0 < settings["edge_s"] < settings["hold_s"]
            < settings["off_s"] - settings["enable_s"]
            and settings["stop_s"] - settings["off_s"] > settings["hold_s"]):
        raise ValueError("Stimulus timing does not contain full active/shutdown hold intervals")
    models = Path(tool_config["pdk_root"]) / "sky130A/libs.tech/ngspice/sky130.lib.spice"
    if not models.is_file() or not dut.is_file():
        raise RuntimeError("Configured model library or DUT file is missing")
    ngspice = tool_config.get("tools", {}).get("ngspice", "ngspice")
    grid = config["profiles"][profile]
    cases = list(itertools.product(grid["corners"], grid["temperatures"], grid["supplies"]))
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")

    def run_case(item):
        index, (corner, temperature, supply) = item
        case_start = time.monotonic()
        case = {"corner": corner, "temperature": temperature, "supply": supply,
                "status": "pass", "analyses": {}, "directory": f"case_{index:03d}"}
        directory = outdir / case["directory"]
        replacements = {
            "PDK_MODELS": str(models), "DUT": str(dut), "CORNER": str(corner),
            "TOP": config.get("top", "LELOTEMP_BIAS_IBP"), "TEMP": str(temperature),
            "SUPPLY": str(supply), "ENABLE": str(settings["enable_s"]),
            "ENABLE_END": str(settings["enable_s"] + settings["edge_s"]),
            "OFF": str(settings["off_s"]), "OFF_END": str(settings["off_s"] + settings["edge_s"]),
            "STOP": str(settings["stop_s"]), "STEP": str(settings["step_s"]),
        }
        for analysis in selected:
            analysis_start = time.monotonic()
            folder = directory / analysis
            folder.mkdir(parents=True, exist_ok=True)
            deck = (project / "testbenches" / f"{analysis}.spice").read_text()
            for key, value in replacements.items():
                deck = deck.replace(f"@{key}@", value)
            # Tokens in explanatory comments are harmless, but circuit tokens
            # must all resolve. Avoid hidden dependence on a user .spiceinit.
            if any(re.search(r"@[A-Z_]+@", line) for line in deck.splitlines() if not line.startswith("*")):
                raise RuntimeError("Unresolved testbench placeholder")
            (folder / "case.spice").write_text(deck)
            data_path = folder / f"{analysis}.dat"
            data_path.unlink(missing_ok=True)
            command = [str(ngspice), "-n", "-D", "ngbehavior=hsa", "-D", "skywaterpdk", "-b", "case.spice"]
            try:
                with (folder / "ngspice.log").open("w") as log:
                    process = subprocess.run(command, cwd=folder, env=env, stdout=log,
                                             stderr=subprocess.STDOUT,
                                             timeout=tool_config.get("timeout_s", 180))
                log_text = (folder / "ngspice.log").read_text()
                if process.returncode != 0 or re.search(
                    r"(?im)^\s*(?:fatal(?:\s|:)|error(?:\s|:)|.*(?:simulation interrupted|timestep too small|unknown subckt|no such vector|redefinition of \.subckt))",
                    log_text,
                ):
                    raise RuntimeError("ngspice reported an error; inspect ngspice.log")
                data = read_table(data_path, 3 if analysis == "stability" else 7)
                if analysis == "dc":
                    metrics = measure_dc(data, supply)
                elif analysis == "tran":
                    dc = case["analyses"].get("dc", {})
                    target = (dc["currents_a"] + [dc["voltage_v"]]) if "currents_a" in dc else None
                    metrics = measure_tran(data, settings, supply, target)
                else:
                    metrics = measure_stability(data)
                metrics.update(status="pass", elapsed_s=time.monotonic() - analysis_start)
                case["analyses"][analysis] = metrics
                # DC values define transfer/power. Tran-only mode still reports
                # useful active values, without pretending to be the full suite.
                for key, value in metrics.items():
                    if key not in ("status", "elapsed_s") and (key not in case or analysis != "tran"):
                        case[key] = value
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                case["status"] = "fail"
                case["analyses"][analysis] = {"status": "fail", "error": str(exc),
                                              "elapsed_s": time.monotonic() - analysis_start}
        case["elapsed_s"] = time.monotonic() - case_start
        (directory / "result.json").write_text(json.dumps(case, indent=2, allow_nan=False) + "\n")
        return case

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(settings["jobs"]))) as pool:
        results = list(pool.map(run_case, enumerate(cases)))
    result = {"status": "pass" if all(case["status"] == "pass" for case in results) else "fail",
              "view": view, "profile": profile, "analyses": selected,
              "cases": results, "elapsed_s": time.monotonic() - started,
              "settings": settings, "model_library": str(models)}
    (outdir / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
