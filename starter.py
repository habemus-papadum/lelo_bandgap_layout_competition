"""Reproducible, unwired parts trays derived from the fixed schematic.

This is deliberately a parser for the bundled, parameter-free assembly netlist,
not a general SPICE elaborator. Unsupported constructs fail rather than omit parts.
"""
from collections import Counter
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parent
PNP_MODEL = 'sky130_fd_pr__pnp_05v5_W3p40L3p40'
PNP_CELL = 'sky130_fd_pr__rf_pnp_05v5_W3p40L3p40'
GAP = 1000  # 5 um of clearance between actual painted bounds, at 0.005 um/unit.


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subcircuits(text):
    definitions, current = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('*'):
            continue
        fields = line.split()
        command = fields[0].lower()
        if command == '.subckt':
            if current is not None or fields[1] in definitions:
                raise ValueError(f'Duplicate or nested subcircuit: {line}')
            current = fields[1]
            definitions[current] = {'ports': fields[2:], 'devices': []}
        elif command == '.ends':
            if current is None:
                raise ValueError('Unexpected .ends')
            current = None
        elif command.startswith('x') and current is not None:
            positional = [f for f in fields if '=' not in f]
            parameters = [f.lower() for f in fields if '=' in f]
            definitions[current]['devices'].append((positional[0], positional[1:-1], positional[-1], parameters))
        else:
            raise ValueError(f'Unsupported schematic statement: {line}')
    if current is not None:
        raise ValueError(f'Unterminated subcircuit: {current}')
    return definitions


def inventory(definitions, top, tiles):
    result = []

    def visit(name, path, active):
        if name in active or name not in definitions:
            raise ValueError(f'Cyclic or missing schematic assembly: {name}')
        devices = definitions[name]['devices']
        if not devices or len({d[0].lower() for d in devices}) != len(devices):
            raise ValueError(f'Empty assembly or duplicate instances: {name}')
        for instance, nets, cell, parameters in devices:
            source = '/'.join((*path, instance))
            if any(p != 'm=1' for p in parameters):
                raise ValueError(f'Unsupported assembly multiplicity/parameters: {source}')
            if cell in tiles or cell == PNP_MODEL:
                expected_ports = 3 if cell == PNP_MODEL else len(definitions[cell]['ports'])
                if len(nets) != expected_ports:
                    raise ValueError(f'Incorrect pin count: {source}')
                result.append({'instance': source.replace('/', '__'), 'schematic_path': source,
                               'cell': PNP_CELL if cell == PNP_MODEL else cell})
            else:
                if cell not in definitions or len(nets) != len(definitions[cell]['ports']):
                    raise ValueError(f'Unknown cell or incorrect pin count: {source}: {cell}')
                visit(cell, (*path, instance), (*active, name))

    visit(top, (), ())
    names = [r['instance'] for r in result]
    if len(set(names)) != len(names) or any(not re.fullmatch(r'[A-Za-z0-9_<>]+', n) for n in names):
        raise ValueError('Ambiguous or unsupported flattened instance names')
    return sorted(result, key=lambda r: (r['cell'], r['schematic_path']))


def painted_bounds(path):
    body = path.read_text()
    if not body.startswith('magic\ntech sky130A\nmagscale 1 2\n') or re.search(r'^use ', body, re.M):
        raise ValueError(f'Expected a flat Sky130A tile on the bundled grid: {path}')
    rectangles, layer = [], None
    for line in body.splitlines():
        if line.startswith('<< '):
            layer = line[3:-3]
        elif layer not in ('checkpaint', 'labels', 'properties', 'end', None) and line.startswith(('rect ', 'tri ')):
            rectangles.append([int(n) for n in line.split()[1:5]])
    if not rectangles:
        raise ValueError(f'No painted geometry: {path}')
    return [min(r[0] for r in rectangles), min(r[1] for r in rectangles),
            max(r[2] for r in rectangles), max(r[3] for r in rectangles)]


def tray(parts, bounds, ports=(), grouped=True):
    counts = Counter(p['cell'] if grouped else 'all' for p in parts)
    columns = min(range(1, len(parts) + 1), key=lambda c: (
        max(c, sum(math.ceil(n / c) for n in counts.values())),
        abs(c - sum(math.ceil(n / c) for n in counts.values())), c))
    span = max(max(b[2] - b[0], b[3] - b[1]) for b in bounds.values())
    pitch = math.ceil((span + GAP) / 200) * 200
    lines = ['magic', 'tech sky130A', 'magscale 1 2', 'timestamp 0']
    row, previous, offset = 0, None, 0
    placed = []
    for part in sorted(parts, key=lambda p: (p['cell'], p['instance'])):
        cell = part['cell']
        if grouped and previous is not None and cell != previous:
            row += math.ceil(offset / columns)
            offset = 0
        b = bounds[cell]
        x, y = (offset % columns) * pitch - b[0], (row + offset // columns) * pitch - b[1]
        lines += [f'use {cell} {part["instance"]}', f'transform 1 0 {x} 0 1 {y}',
                  'box ' + ' '.join(map(str, b))]
        placed.append(dict(part, x_units=x, y_units=y))
        previous, offset = cell, offset + 1
    lines.append('<< labels >>')
    for number, port in enumerate(ports, 1):
        y = (number - 1) * 800
        lines += [f'rlabel space -2000 {y} -2000 {y} 0 {port}',
                  f'port {number} nsew signal bidirectional']
    lines += ['<< end >>', '']
    return '\n'.join(lines), placed


def render(root=ROOT):
    config = yaml.safe_load((root / 'competition.yaml').read_text())
    source = root / config['lvs_schematic']
    immutable = json.loads((root / 'cells/manifest.json').read_text())['immutable_magic']
    tiles = {Path(name).stem: root / name for name in immutable}
    for name, expected in immutable.items():
        if digest(root / name) != expected:
            raise ValueError(f'Provided tile was modified: {name}')
    parts = inventory(subcircuits(source.read_text()), config['top'], tiles)
    files = dict(tiles, **{PNP_CELL: root / 'pdk/sky130A/libs.ref/sky130_fd_pr/mag' / (PNP_CELL + '.mag')})
    names = {p['cell'] for p in parts}
    bounds = {name: painted_bounds(files[name]) for name in names}
    layout, placed = tray(parts, bounds, config['ports'])
    taps = [{'instance': 'sample_' + name, 'cell': name} for name in sorted(tiles) if 'TAP' in name]
    palette, _ = tray(taps, {p['cell']: painted_bounds(files[p['cell']]) for p in taps}, grouped=False)
    table = io.StringIO(newline='')
    writer = csv.DictWriter(table, fieldnames=['instance', 'schematic_path', 'cell', 'x_units', 'y_units'], lineterminator='\n')
    writer.writeheader()
    writer.writerows(placed)
    manifest = {'schema_version': 1, 'source': config['lvs_schematic'], 'source_sha256': digest(source),
                'coordinate_unit_um': 0.005, 'minimum_paint_gap_um': GAP * 0.005,
                'counts': dict(sorted(Counter(p['cell'] for p in parts).items())),
                'cells': {name: {'path': str(files[name].relative_to(root)), 'sha256': digest(files[name]),
                                 'paint_bounds': painted_bounds(files[name])}
                          for name in sorted(names | {p['cell'] for p in taps})}}
    return {config['top'] + '.mag': layout, 'tap_palette.mag': palette,
            'inventory.csv': table.getvalue(), 'provenance.json': json.dumps(manifest, indent=2) + '\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Reject stale committed templates without writing.')
    args = parser.parse_args()
    directory = ROOT / 'templates/provided'
    for name, content in render().items():
        path = directory / name
        if args.check:
            if not path.is_file() or path.read_text() != content:
                raise SystemExit(f'Stale starter: {path}; regenerate with uv run python -m starter')
        else:
            directory.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print('Provided starter is reproducible.' if args.check else f'Generated {directory}')


if __name__ == '__main__':
    main()
