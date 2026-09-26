#!/usr/bin/env python3
"""Individually runnable checks for the Sky130 bandgap layout competition."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: python3 -m pip install PyYAML")

import physical

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import project


def read_yaml(path):
    return yaml.safe_load(Path(path).read_text()) or {}


def local_config():
    local = project.local_settings()
    local["pdk_root"] = str(project.pdk_root())
    configured = local.get("tools", {})
    local["tools"] = {}
    for name in ("magic", "netgen", "ngspice", "xschem"):
        value = str(configured.get(name, name))
        if "/" in value:
            value = Path(value).expanduser()
            value = str(value if value.is_absolute() else ROOT / value)
        resolved = shutil.which(value)
        if not resolved and name != "xschem":
            raise RuntimeError(f"Missing executable: {name} ({value})")
        local["tools"][name] = resolved
    local.setdefault("timeout_s", 180)
    return local


class Evaluation:
    def __init__(self, args):
        self.args = args
        self.config = read_yaml(ROOT / "competition.yaml")
        self.local = local_config()
        self.layout = (args.layout or ROOT / self.config["reference_layout"]).resolve()
        if self.layout.stem != self.config["top"]:
            raise RuntimeError(f"Name the top layout {self.config['top']}.mag")
        self.out = args.out.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.cells, self.primitives = physical.hierarchy(ROOT, self.layout, self.local["pdk_root"], args.track)
        # Hash actual files, not timestamps. Existing reports cannot validate a changed submission.
        pdk = Path(self.local["pdk_root"]) / "sky130A"
        required = [pdk / "libs.tech/magic/sky130A.tech", pdk / "libs.tech/magic/sky130A.magicrc",
                    pdk / "libs.tech/netgen/sky130A_setup.tcl",
                    pdk / "libs.tech/ngspice/sky130.lib.spice"]
        for path in required:
            if not path.is_file():
                raise RuntimeError(f"Missing PDK file: {path}")
        pdk_files = set(required)
        for rel, pattern in [("libs.ref/sky130_fd_pr/spice", "*"), ("libs.tech/ngspice", "*"),
                             ("libs.tech/magic", "*.tcl")]:
            pdk_files.update(p for p in (pdk/rel).rglob(pattern) if p.is_file())
        pdk_digest = hashlib.sha256()
        for p in sorted(pdk_files):
            pdk_digest.update(str(p.relative_to(pdk)).encode())
            pdk_digest.update(p.read_bytes())
        self.pdk_hash = pdk_digest.hexdigest()
        measurement_config = {key: value for key, value in self.config.items() if key != "scoring"}
        inputs = {"layout": {name: physical.sha(path) for name, path in sorted(self.cells.items())},
                  "competition": measurement_config, "pdk_sha256": self.pdk_hash,
                  "track": args.track, "mode": args.mode,
                  "cell_manifest": physical.sha(ROOT / "cells/manifest.json"),
                  "project_paths": physical.sha(ROOT / "project.py")}
        for folder in ("tools", "testbenches", "schematic"):
            for p in sorted((ROOT/folder).rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".log"):
                    inputs[str(p.relative_to(ROOT))] = physical.sha(p)
        inputs["executables"] = {name: physical.sha(path) for name, path in self.local["tools"].items() if path}
        self.signature = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()

    def previous(self, name):
        path = self.out / (name + ".json")
        if not path.exists():
            raise RuntimeError(f"Run {name} first (missing {path})")
        obj = json.loads(path.read_text())
        if obj.get("signature") != self.signature or obj.get("status") != "pass":
            raise RuntimeError(f"{name} result is failed or stale; rerun that check")
        for artifact, digest in obj.get("artifacts", {}).items():
            if not Path(artifact).is_file() or physical.sha(artifact) != digest:
                raise RuntimeError(f"{name} output changed or disappeared: {artifact}")
        return obj

    def execute(self, name, callback):
        directory = Path(tempfile.mkdtemp(prefix=name + "-", dir=self.out))
        start = time.monotonic()
        result = {"check": name, "signature": self.signature, "directory": str(directory),
                  "pdk_sha256": self.pdk_hash, "status": "fail",
                  "competition_sha256": physical.sha(ROOT/"competition.yaml")}
        error = None
        try:
            details = callback(directory)
            result.update(details)
            if details.get("status") == "fail":
                raise RuntimeError(f"{name} reported failures; see {directory}")
            result["status"] = "pass"
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            error = exc
            result["error"] = str(exc)
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        # Bind all retained artifacts to the report, including simulation measures/decks.
        result["artifacts"] = {str(p): physical.sha(p) for p in directory.rglob("*")
                               if p.is_file() and p != directory / "result.json"}
        (directory / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        (self.out / (name + ".json")).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(f"{name}: {result['status'].upper()} ({result['elapsed_s']:.3f}s) — {self.out/(name+'.json')}", flush=True)
        if error:
            raise RuntimeError(str(error))
        return result

    def doctor(self, directory):
        versions = {}
        for name, flag in [("magic", "--version"), ("ngspice", "--version")]:
            text, _ = physical.run([self.local["tools"][name], flag], directory, directory/(name+"-version.log"))
            versions[name] = text.strip()
        script = directory / "netgen-health.tcl"
        script.write_text('puts BG_NETGEN_OK\nquit\n')
        text, _ = physical.run([self.local["tools"]["netgen"], "-batch", "source", str(script)],
                               directory, directory / "netgen.log")
        if "BG_NETGEN_OK" not in text:
            raise RuntimeError("Netgen Tcl interpreter did not complete")
        pdk = Path(self.local["pdk_root"]) / "sky130A"
        # A real PDK-model operating point, not just executable discovery.
        (directory / "spice.rc").write_text("set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\n")
        deck = directory / "model.spice"
        deck.write_text(f'* PDK model smoke check\n.lib "{pdk}/libs.tech/ngspice/sky130.lib.spice" tt\n'
                        'Vd d 0 1.8\nVg g 0 0.8\nX1 d g 0 0 sky130_fd_pr__nfet_01v8 w=1 l=0.15\n'
                        '.control\nop\nprint i(Vd)\necho BG_MODEL_OK\nquit\n.endc\n.end\n')
        env = dict(os.environ, PDK_ROOT=self.local["pdk_root"], SPICE_USERINIT_DIR=str(directory))
        text, _ = physical.run([self.local["tools"]["ngspice"], "-b", str(deck)], directory,
                               directory / "model.log", env, self.local["timeout_s"])
        if "BG_MODEL_OK" not in text or "Error" in text:
            raise RuntimeError(f"PDK model smoke check failed; see {directory/'model.log'}")
        return {"versions": versions, "resolved_cells": len(self.cells),
                "pdk_cells": sorted(self.primitives), "tools": self.local["tools"]}

    def physical(self, action, directory):
        return physical.magic_check(ROOT, self.config, self.local, self.cells, directory, action, self.args.mode)

    def lvs(self, directory):
        result = self.physical("lvs", directory)
        result.update(physical.lvs(self.local, result["netlist"], ROOT/self.config["lvs_schematic"],
                                   self.config["top"], directory))
        return result

    def extract(self, directory):
        result = self.physical("extract", directory)
        normalized, reduced = directory / "layout.spice", directory / "connectivity.spice"
        physical.normalize_extraction(result["netlist"], normalized, self.config)
        result.update(physical.contract_parasitics(normalized, reduced))
        result.update(physical.lvs(self.local, reduced, ROOT/self.config["lvs_schematic"],
                                   self.config["top"], directory))
        if self.args.mode == "rc" and result["contracted_resistors"] == 0:
            raise RuntimeError("RC extraction produced no wiring resistors")
        result.update(netlist=str(normalized), mode=self.args.mode)
        return result

    def simulate(self, directory, view):
        from simulation import run_simulation
        dut = ROOT / self.config["schematic"]
        if view == "layout":
            dut = Path(self.previous("extract")["netlist"])
        return run_simulation(ROOT, self.config, self.local, dut, view, self.args.profile,
                              directory, analyses=self.args.analysis)

    def score(self, directory):
        for name in ("doctor", "drc", "lvs", "extract"):
            self.previous(name)
        area = self.previous("area")["area_um2"]
        sch = self.previous("simulate-schematic-" + self.args.profile)
        lay = self.previous("simulate-layout-" + self.args.profile)
        if any(set(r.get("analyses", [])) != {"dc", "tran", "stability"} for r in (sch, lay)):
            raise RuntimeError("Scoring requires all three analyses, including a separate DC operating point")
        limits = self.config["scoring"]
        key = lambda c: (c["corner"], c["temperature"], c["supply"])
        baseline = {key(c): c for c in sch["cases"]}
        extracted = {key(c): c for c in lay["cases"]}
        profile = self.config["profiles"][self.args.profile]
        expected = {(c, t, v) for c in profile["corners"] for t in profile["temperatures"] for v in profile["supplies"]}
        if set(baseline) != expected or set(extracted) != expected:
            raise RuntimeError("Simulation results do not contain the complete selected profile")
        failures, deviation, r_settle, r_power = [], 0.0, 1.0, 1.0
        for condition in sorted(expected):
            b, x = baseline[condition], extracted[condition]
            for label, case in [("schematic", b), ("layout", x)]:
                required = ["currents_a", "voltage_v", "settling_s", "power_w", "leakage_a", "phase_margin_deg"]
                if any(k not in case for k in required):
                    raise RuntimeError("Scoring needs DC, transient and stability results; rerun all analyses")
                nums = case["currents_a"] + [case[k] for k in required[1:]]
                if len(case["currents_a"]) != 4 or not all(math.isfinite(n) for n in nums):
                    raise RuntimeError(f"Incomplete or nonfinite measurements at {condition}")
                valid = (all(limits["minimum_current_a"] <= i <= limits["maximum_current_a"] for i in case["currents_a"])
                         and limits["voltage_range_v"][0] <= case["voltage_v"] <= limits["voltage_range_v"][1]
                         and 0 < case["settling_s"] <= limits["maximum_settling_s"]
                         and 0 < case["power_w"] <= limits["maximum_power_w"]
                         and abs(case["leakage_a"]) <= limits["maximum_leakage_a"]
                         and case["phase_margin_deg"] >= limits["minimum_phase_margin_deg"])
                if not valid:
                    failures.append({"view": label, "condition": condition})
            if min(b["settling_s"], b["power_w"], *b["currents_a"]) <= 0:
                raise RuntimeError("Baseline has invalid score denominators")
            deviation = max(deviation, abs(x["voltage_v"]-b["voltage_v"])/limits["voltage_deviation_v"],
                            *(abs(a-bv)/(limits["current_deviation_fraction"]*bv)
                              for a, bv in zip(x["currents_a"], b["currents_a"])))
            r_settle = max(r_settle, x["settling_s"]/b["settling_s"])
            r_power = max(r_power, x["power_w"]/b["power_w"])
        reference = limits["reference_area_um2"]
        if reference is None or reference <= 0 or area <= 0:
            raise RuntimeError("Positive measured reference area must be configured before scoring")
        score = 100 * reference / area / ((1+deviation**2)*math.sqrt(r_settle*r_power)) if not failures else 0.0
        official = bool(limits["qualified"] and self.args.profile == "corners" and self.args.mode == "rc")
        result = {"status": "pass" if not failures else "fail",
                  "score": score, "eligible": not failures, "electrical_failures": failures,
                  "official": official, "track": self.args.track, "area_um2": area,
                  "worst_normalized_deviation": deviation, "settling_ratio": r_settle, "power_ratio": r_power,
                  "scoring_configuration": limits}
        (directory / "score.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"Score {score:.3f}; eligible={not failures}; {'qualified profile' if official else 'development result'}", flush=True)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "drc", "lvs", "area", "extract", "simulate", "score", "all"])
    parser.add_argument("--layout", type=Path, help="Top Magic file; default is the supplied reference")
    parser.add_argument("--out", type=Path, default=ROOT/"runs/reference")
    parser.add_argument("--track", choices=["provided", "custom"], default="provided")
    parser.add_argument("--mode", choices=["c", "rc"], default="rc")
    parser.add_argument("--view", choices=["schematic", "layout"], default="schematic")
    parser.add_argument("--profile", choices=["typical", "corners"], default="typical")
    parser.add_argument("--analysis", action="append", choices=["dc", "tran", "stability"],
                        help="Run only this analysis; may be repeated (default: all three)")
    args = parser.parse_args()
    try:
        evaluation = Evaluation(args)
        commands = [args.command] if args.command != "all" else ["doctor", "drc", "lvs", "area", "extract", "simulate", "score"]
        for command in commands:
            if command == "simulate":
                views = [args.view] if args.command != "all" else ["schematic", "layout"]
                for view in views:
                    name = f"simulate-{view}-{args.profile}"
                    evaluation.execute(name, lambda d, view=view: evaluation.simulate(d, view))
            else:
                method = getattr(evaluation, command) if command not in ("drc", "area") else lambda d, c=command: evaluation.physical(c, d)
                evaluation.execute(command, method)
    except (RuntimeError, OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
