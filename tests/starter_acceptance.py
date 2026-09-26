"""Real Magic/Netgen validation of the intentionally disconnected starter.

Run with uv run python tests/starter_acceptance.py --pdk-root pdk.
Artifacts are retained under runs/ for inspection, including expected failures.
"""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import check
import physical
import project
import starter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk-root', type=Path)
    args = parser.parse_args()
    local = check.local_config()
    local['pdk_root'] = str(project.pdk_root(args.pdk_root))
    config = check.read_yaml(ROOT / 'competition.yaml')
    (ROOT / 'runs').mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='starter-validation-', dir=ROOT / 'runs'))
    print(f'Artifacts: {out}', flush=True)
    summary = {'pdk_root': local['pdk_root'], 'tiles': {}}
    template = ROOT / 'templates/provided'
    manifest = json.loads((template / 'provenance.json').read_text())
    for name, content in starter.render().items():
        assert (template / name).read_text() == content, f'Stale template: {name}'

    def stage(name):
        directory = out / name
        directory.mkdir()
        return directory

    # Positive baseline, plus positive LVS for each kind of electrical part.
    reference, _ = physical.hierarchy(ROOT, ROOT / config['reference_layout'], local['pdk_root'], 'provided')
    physical.magic_check(ROOT, config, local, reference, stage('reference-drc'), 'drc')
    directory = stage('reference-lvs')
    raw = physical.magic_check(ROOT, config, local, reference, directory, 'lvs')['netlist']
    physical.lvs(local, raw, ROOT / config['lvs_schematic'], config['top'], directory)
    print('PASS reference DRC and LVS', flush=True)
    for cell in manifest['counts']:
        path = ROOT / manifest['cells'][cell]['path']
        if cell == starter.PNP_CELL:
            path = Path(local['pdk_root']) / 'sky130A/libs.ref/sky130_fd_pr/mag' / (cell + '.mag')
        assert physical.sha(path) == manifest['cells'][cell]['sha256'], f'Cell differs from validated template bounds: {cell}'
        directory = stage(cell)
        cell_config = dict(config, top=cell)
        raw = physical.magic_check(ROOT, cell_config, local, {cell: path}, directory, 'lvs')['netlist']
        schematic = ROOT / config['lvs_schematic']
        if cell == starter.PNP_CELL:
            schematic = directory / 'expected.spice'
            schematic.write_text(f'.subckt {cell} Emitter Collector Base\n'
                                 f'XQ Collector Base Emitter {starter.PNP_MODEL} m=1\n.ends\n')
        physical.lvs(local, raw, schematic, cell, directory)
        summary['tiles'][cell] = {'lvs': 'pass'}
        # Report isolated tile DRC without claiming a floating tray is finished.
        drc_dir = stage(cell + '-drc')
        try:
            drc = physical.magic_check(ROOT, cell_config, local, {cell: path}, drc_dir, 'drc')
            summary['tiles'][cell]['drc_violations'] = drc['violations']
        except RuntimeError as exc:
            if 'DRC violations' not in str(exc):
                raise
            summary['tiles'][cell]['drc'] = str(exc)
        print(f'PASS {cell} LVS; DRC: {summary["tiles"][cell]}', flush=True)

    entry = project.create_submission(out / "student's entry", 'provided')
    cells, _ = physical.hierarchy(ROOT, entry / (config['top'] + '.mag'), local['pdk_root'], 'provided')
    directory = stage('tray-extraction')
    raw = Path(physical.magic_check(ROOT, config, local, cells, directory, 'extract', mode='c')['netlist'])
    # Count actual extracted primitive records with merging disabled by 'lvs' style.
    counts = Counter()
    for statement in physical.statements(raw.read_text()):
        fields = statement.split()
        if fields and fields[0].lower().startswith('x'):
            model = [f for f in fields if '=' not in f][-1]
            counts[model] += 1
    expected = {'sky130_fd_pr__pfet_01v8': 128, 'sky130_fd_pr__pfet_01v8_lvt': 24,
                'sky130_fd_pr__nfet_01v8': 38, 'sky130_fd_pr__cap_mim_m3_1': 13,
                'sky130_fd_pr__res_high_po': 16, starter.PNP_MODEL: 9}
    assert counts == expected, (counts, expected)
    summary['extracted_devices'] = dict(counts)
    # Full-circuit LVS must actually run and report non-equivalence.
    directory = stage('tray-lvs')
    raw = physical.magic_check(ROOT, config, local, cells, directory, 'lvs')['netlist']
    try:
        physical.lvs(local, raw, ROOT / config['lvs_schematic'], config['top'], directory)
    except RuntimeError as exc:
        report = (directory / 'lvs.log').read_text()
        assert 'LVS failed' in str(exc) and re.search(r'do not match|mismatch', report, re.I), report
    else:
        raise AssertionError('An unconnected tray unexpectedly passed circuit LVS')
    summary['circuit_lvs'] = 'expected mismatch'
    print('PASS 228 extracted devices; disconnected circuit fails LVS as expected', flush=True)
    directory = stage('tray-drc')
    try:
        result = physical.magic_check(ROOT, config, local, cells, directory, 'drc')
        summary['tray_drc_violations'] = result['violations']
    except RuntimeError as exc:
        if 'DRC violations' not in str(exc):
            raise
        summary['tray_drc'] = str(exc)
    # Load through the actual editor startup/search paths, from a submission
    # outside the template directory. Inspect every extraction feedback box.
    directory = stage('direct-magic')
    script = '''puts "BG_DIRECT_TOP [cellname list window]"
select top cell
select visible
puts "BG_VISIBLE_PAINT [lindex [what -list] 0]"
select clear
flatten starter_probe
load starter_probe
extract path $env(BG_EXT)
extract all
feedback save $env(BG_FEEDBACK)
puts BG_DIRECT_DONE
quit -noprompt
'''
    feedback = directory / 'feedback.txt'
    proc = subprocess.run([local['tools']['magic'], '-dnull', '-noconsole', '-rcfile',
                           str(ROOT / 'magicrc'), str(ROOT / 'tools/magic_open.tcl')],
                          input=script, text=True, capture_output=True, cwd=entry, timeout=30,
                          env=dict(os.environ, PDK_ROOT=local['pdk_root'], MAGTYPE='mag',
                                   BANDGAP_LAYOUT=config['top'] + '.mag',
                                   BG_EXT=str(directory), BG_FEEDBACK=str(feedback)))
    text = proc.stdout + proc.stderr
    (directory / 'magic.log').write_text(text)
    assert proc.returncode == 0 and 'BG_DIRECT_DONE' in text, text
    assert 'BG_DIRECT_TOP ' + config['top'] in text, text
    visible = set(re.search(r'^BG_VISIBLE_PAINT (.*)$', text, re.M)[1].split())
    assert {'nmos', 'pmos', 'ppolyres', 'mimcap', 'nbase'} <= visible, visible
    assert not re.search(r'bad file path|couldn.t be read|unavailable|Error:|invalid command', text, re.I), text
    feedback_text = feedback.read_text()
    actual_boxes = [tuple(map(int, s.split())) for s in re.findall(r'^box (.+)$', feedback_text, re.M)]
    expected_boxes = []
    for part in csv.DictReader((entry / 'inventory.csv').read_text().splitlines()):
        if part['cell'] == 'REYATR_RES_36C2F0':
            x, y = int(part['x_units']), int(part['y_units'])
            # Three uncontacted poly strips already present in the immutable tile.
            for bottom in (40, 200, 680):
                expected_boxes.append((x + 288, y + bottom, x + 2912, y + bottom + 80))
    assert sorted(actual_boxes) == sorted(expected_boxes), feedback_text
    messages = re.findall(r'^feedback add "(.+)" pale$', feedback_text, re.M)
    assert len(messages) == 24 and set(messages) == {'device missing 2 terminals'}, feedback_text
    summary['extraction_feedback'] = '24 known uncontacted resistor-strip warnings; locations verified'
    print('PASS direct Magic library loading and all 24 expected feedback locations', flush=True)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
