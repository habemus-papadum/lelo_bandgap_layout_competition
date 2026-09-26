"""Magic and Netgen checks. No dependency on the source repository or CIC tools."""
from pathlib import Path
import hashlib
import json
import os
import re
import shlex
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, directory, log, env=None, timeout=180):
    start = time.monotonic()
    with Path(log).open("w") as stream:
        try:
            proc = subprocess.run(command, cwd=directory, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Timed out after {timeout}s; see {log}") from exc
    text = Path(log).read_text(errors="replace")
    if proc.returncode:
        raise RuntimeError(f"Exit {proc.returncode}: {command[0]}; see {log}")
    return text, time.monotonic() - start


def hierarchy(project, layout, pdk_root, track):
    """Resolve every child before Magic can silently replace it with an empty cell."""
    project, layout = Path(project).resolve(), Path(layout).resolve()
    primitive_dir = Path(pdk_root) / "sky130A/libs.ref/sky130_fd_pr/mag"
    library = project / "cells/REY_ATR_SKY130A"
    manifest = json.loads((project / "cells/manifest.json").read_text())
    immutable = {Path(p).stem: digest for p, digest in manifest["immutable_magic"].items()}
    seen, active, primitives = {}, set(), set()
    # Assembly may contain routing and substrate contacts, but not new transistors.
    routing = {"checkpaint", "locali", "viali", "metal1", "via1", "metal2", "via2",
               "metal3", "via3", "metal4", "via4", "metal5", "psubdiff", "psubdiffcont",
               "nsubdiff", "nsubdiffcont", "nwell", "pwell", "labels", "properties", "end"}

    def visit(path, is_pdk=False):
        path = path.resolve()
        if not any(path.is_relative_to(root) for root in (project, layout.parent, primitive_dir.resolve())):
            raise RuntimeError(f"Cell escapes the project/submission directories: {path}")
        name = path.stem
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise RuntimeError(f"Unsupported Magic cell name: {name}")
        if name in active:
            raise RuntimeError(f"Cyclic Magic hierarchy at {name}")
        if name in seen:
            if seen[name] != path:
                raise RuntimeError(f"Two files define cell {name}: {seen[name]} and {path}")
            return
        if not path.is_file():
            raise RuntimeError(f"Missing Magic cell: {path}")
        body = path.read_text()
        if not body.startswith("magic\n") or not re.search(r"^tech sky130A$", body, re.M):
            raise RuntimeError(f"Not a Sky130A Magic layout: {path}")
        if is_pdk:
            primitives.add(name)
        elif track == "provided":
            if name in immutable:
                if sha(path) != immutable[name]:
                    raise RuntimeError(f"Provided tile was modified: {name}; use the custom track")
            else:
                layers = set(re.findall(r"^<< (\S+) >>$", body, re.M))
                if layers - routing:
                    raise RuntimeError(f"New device layers in assembly {name}: {sorted(layers-routing)}")
        elif track == "custom" and name in immutable:
            raise RuntimeError(f"Custom track must not instantiate supplied tile {name}")
        seen[name] = path
        active.add(name)
        for line in body.splitlines():
            if not line.startswith("use "):
                continue
            parts = shlex.split(line)
            child = parts[1]
            if child.startswith("sky130_fd_pr__"):
                candidate = primitive_dir / (child + ".mag")
                visit(candidate, True)
                continue
            # Explicit use paths take precedence and must actually resolve.
            if len(parts) > 3:
                candidate = path.parent / parts[3] / (child + ".mag")
                if not candidate.is_file():
                    raise RuntimeError(f"Missing child {child} referenced by {path}: {candidate}")
            else:
                candidates = {p.resolve() for p in [path.parent / (child + ".mag"),
                                                    library / (child + ".mag")]
                              if p.is_file()}
                if len(candidates) != 1:
                    raise RuntimeError(f"Missing or ambiguous child {child} in {path}")
                candidate = candidates.pop()
            visit(candidate)
        active.remove(name)

    visit(layout)
    return seen, primitives


def stage_cells(cells, directory):
    """Private copies use one search directory, so global Magic paths cannot fill gaps."""
    dest = directory / "cells"
    dest.mkdir()
    for name, source in cells.items():
        lines = []
        for line in source.read_text().splitlines():
            if line.startswith("use "):
                parts = shlex.split(line)
                line = " ".join(parts[:3])
            lines.append(line)
        (dest / (name + ".mag")).write_text("\n".join(lines) + "\n")
    return dest


def magic_check(project, config, local, cells, directory, action, mode="rc"):
    directory = Path(directory).resolve()
    staged = stage_cells(cells, directory)
    env = dict(os.environ, PDK_ROOT=str(local["pdk_root"]), MAGTYPE="mag",
               BG_TOP=config["top"], BG_CELLS=str(staged), BG_ACTION=action,
               BG_MODE=mode, BG_CTHRESH=str(config["extraction"]["capacitance_threshold_ff"]),
               BG_RTOL=str(config["extraction"]["resistance_tolerance"]),
               BG_DRC_STYLE=config["drc"]["style"])
    rc = directory / "magicrc"
    rc.write_text('source $env(PDK_ROOT)/sky130A/libs.tech/magic/sky130A.magicrc\n'
                  'path search $env(BG_CELLS)\nset SUB 0\n')
    text, elapsed = run([local["tools"]["magic"], "-dnull", "-noconsole", "-rcfile", str(rc),
                         str(Path(project) / "tools/physical.tcl")], directory,
                        directory / "magic.log", env, local["timeout_s"])
    bad = r"couldn.t be read|unavailable|Failure to read|Failed on cell|can't read|invalid command|Error:|BG_ERROR"
    if re.search(bad, text, re.I) or "BG_DONE" not in text:
        raise RuntimeError(f"Magic did not complete a valid {action}; see {directory/'magic.log'}")
    warnings = [line for line in text.splitlines() if re.search(r"warn|error", line, re.I)]
    result = {"elapsed_s": elapsed, "warnings": warnings, "log": str(directory / "magic.log")}
    if action == "drc":
        match = re.search(r"BG_DRC_COUNT (\d+)", text)
        if not match:
            raise RuntimeError("Magic did not return a DRC count")
        result["violations"] = int(match[1])
        if result["violations"]:
            raise RuntimeError(f"{result['violations']} DRC violations; see {directory/'magic.log'}")
    elif action == "area":
        # Read flattened paint coordinates, ignoring labels, checkpaint and editable bbox properties.
        scale = float(re.search(r"BG_SCALE ([\deE.+-]+)", text)[1])
        rects, layer = [], None
        for line in (directory / "area.mag").read_text().splitlines():
            if line.startswith("<< "):
                layer = line[3:-3]
            if layer not in {"checkpaint", "labels", "properties", "end"} and line.startswith(("rect ", "tri ")):
                rects.append([int(n) for n in line.split()[1:5]])
        if not rects:
            raise RuntimeError("No physical geometry for area measurement")
        bbox = [min(r[0] for r in rects), min(r[1] for r in rects),
                max(r[2] for r in rects), max(r[3] for r in rects)]
        result.update(bbox_um=[n * scale for n in bbox],
                      area_um2=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])*scale**2)
    else:
        netlist = directory / "raw.spice"
        if not netlist.is_file() or netlist.stat().st_size == 0:
            raise RuntimeError("Magic produced no extracted netlist")
        result["netlist"] = str(netlist)
    return result


def statements(text):
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("+"):
            if not lines:
                raise RuntimeError("Orphan SPICE continuation")
            lines[-1] += " " + line.lstrip()[1:].strip()
        else:
            lines.append(line.strip())
    return lines


def normalize_extraction(raw, output, config):
    """Verify the actual extracted pins before reordering by their names."""
    lines = statements(Path(raw).read_text())
    top = config["top"]
    expected = config["ports"]
    found, device_names = False, set()
    for i, line in enumerate(lines):
        fields = line.split()
        if not fields:
            continue
        if fields[0].lower() == ".subckt":
            if found:
                raise RuntimeError("Parasitic export must be flat, with one subcircuit")
            if fields[1] not in (top, top + "_flat"):
                raise RuntimeError(f"Unexpected extracted top: {fields[1]}")
            pins = [p.replace("[", "<").replace("]", ">") for p in fields[2:]]
            if len(pins) != len(expected) or {p.upper() for p in pins} != {p.upper() for p in expected}:
                raise RuntimeError(f"Extracted pins differ from the contract: {pins}")
            lines[i] = f".subckt {top} " + " ".join(expected)
            found = True
        elif fields[0].lower() == ".ends":
            lines[i] = f".ends {top}"
        elif fields[0][0].upper() in "XRCMDQ" and not line.startswith("*"):
            key = fields[0].lower()
            if key in device_names:
                raise RuntimeError(f"Duplicate extracted device: {fields[0]}")
            device_names.add(key)
        lines[i] = lines[i].replace("[", "<").replace("]", ">")
    if not found:
        raise RuntimeError("No extracted subcircuit")
    Path(output).write_text("\n".join(lines) + "\n")


NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:[afpnumkgt]|meg)?", re.I)


def contract_parasitics(source, output):
    """Short numeric wiring resistors; drop numeric wiring caps; retain PDK X devices.

    This intentionally accepts only Magic's flat, numeric R/C export. Designed
    Sky130 resistors/capacitors are X instances; an unexpected device fails closed.
    """
    lines = statements(Path(source).read_text())
    parents, pins = {}, set()

    def find(node):
        parents.setdefault(node, node)
        if parents[node] != node:
            parents[node] = find(parents[node])
        return parents[node]

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            # Keep a public port's spelling, otherwise choose deterministically.
            if (b in pins, b) > (a in pins, a):
                a, b = b, a
            parents[b] = a

    for line in lines:
        f = line.split()
        if f and f[0].lower() == ".subckt":
            pins.update(f[2:])
    removed = {"R": 0, "C": 0}
    keep = []
    for line in lines:
        f = line.split("$", 1)[0].split()
        if not f or f[0].startswith(("*", ".")):
            keep.append(line)
            continue
        kind = f[0][0].upper()
        if kind in removed:
            if len(f) != 4 or not NUMBER.fullmatch(f[3]):
                raise RuntimeError(f"Unrecognized parasitic, refusing to remove it: {line}")
            if kind == "R":
                union(f[1], f[2])
            removed[kind] += 1
        elif kind == "X":
            if not any(token.startswith("sky130_fd_pr__") for token in f):
                raise RuntimeError(f"Unresolved non-PDK device in flat extraction: {line}")
            keep.append(line)
        else:
            raise RuntimeError(f"Unexpected extracted device type: {line}")
    if len({find(p) for p in pins}) != len(pins):
        raise RuntimeError("Parasitic contraction would short distinct public ports")
    result = []
    for line in keep:
        f = line.split()
        if f and f[0][0].upper() == "X":
            model = next(i for i, token in enumerate(f) if token.startswith("sky130_fd_pr__"))
            f[1:model] = [find(n) for n in f[1:model]]
            line = " ".join(f)
        result.append(line)
    Path(output).write_text("\n".join(result) + "\n")
    return {"contracted_resistors": removed["R"], "removed_capacitors": removed["C"]}


def lvs(local, extracted, schematic, top, directory):
    # Netgen reports forward references as "undefined" while reading; resolve
    # them in two passes ourselves before accepting its final comparison.
    primitives = {"sky130_fd_pr__" + name for name in
                  ("nfet_01v8", "pfet_01v8", "pfet_01v8_lvt", "res_high_po",
                   "cap_mim_m3_1", "pnp_05v5_w3p40l3p40")}
    for path in (extracted, schematic):
        definitions, calls, current = {}, [], None
        for line in statements(Path(path).read_text()):
            fields = line.lower().split()
            if not fields or fields[0].startswith("*"):
                continue
            if fields[0] == ".subckt":
                current = fields[1]
                if current in definitions:
                    raise RuntimeError(f"Duplicate subcircuit {current} in {path}")
                definitions[current] = 0
            elif fields[0] == ".ends":
                current = None
            elif fields[0][0] == "x":
                if current is None:
                    raise RuntimeError(f"Device outside subcircuit in {path}")
                definitions[current] += 1
                positional = [f for f in fields if "=" not in f]
                calls.append(positional[-1])
            elif current and not fields[0].startswith("."):
                definitions[current] += 1
        if top.lower() not in definitions:
            raise RuntimeError(f"Top cell absent from {path}")
        for cell in calls:
            if cell not in primitives and not definitions.get(cell):
                raise RuntimeError(f"Unresolved or empty subcircuit {cell} in {path}")
    directory = Path(directory).resolve()
    env = dict(os.environ, BG_LAYOUT=str(Path(extracted).resolve()),
               BG_SCHEMATIC=str(Path(schematic).resolve()), BG_TOP=top,
               BG_SETUP=str(Path(local["pdk_root"]) / "sky130A/libs.tech/netgen/sky130A_setup.tcl"))
    script = directory / "compare.tcl"
    script.write_text('lvs [list $env(BG_LAYOUT) $env(BG_TOP)] '
                      '[list $env(BG_SCHEMATIC) $env(BG_TOP)] $env(BG_SETUP) lvs.log\nquit\n')
    text, elapsed = run([local["tools"]["netgen"], "-batch", "source", str(script)], directory,
                        directory / "netgen.log", env, local["timeout_s"])
    report = directory / "lvs.log"
    if not report.is_file():
        raise RuntimeError(f"Netgen did not produce {report}")
    text += report.read_text()
    if ("Final result: Circuits match uniquely." not in text or
            re.search(r"property errors|Final result:.*do not match|failed pin matching|no such file|Error in", text, re.I)):
        raise RuntimeError(f"LVS failed or was incomplete; see {report}")
    return {"match": True, "elapsed_s": elapsed, "report": str(report)}
