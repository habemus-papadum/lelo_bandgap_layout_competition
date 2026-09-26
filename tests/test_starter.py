"""Tool-free checks for a complete, reproducible and non-overlapping parts tray."""
from collections import Counter
import csv
import io
import itertools
import json
import re
import unittest

import starter


class StarterContract(unittest.TestCase):
    def test_committed_assets_are_reproducible(self):
        for name, content in starter.render().items():
            self.assertEqual((starter.ROOT/'templates/provided'/name).read_text(), content, name)

    def test_electrical_inventory_and_paint_clearance(self):
        assets = starter.render()
        body = assets['LELOTEMP_BIAS_IBP.mag']
        manifest = json.loads(assets['provenance.json'])
        parts = list(csv.DictReader(io.StringIO(assets['inventory.csv'])))
        # Independently counted from the top, OTA and bipolar schematic blocks.
        expected = {'REYATR_CAPX1': 13, 'REYATR_LVT_PCH_11C5F0': 12,
                    'REYATR_NCH_4C5F0': 19, 'REYATR_PCH_11C5F0': 6,
                    'REYATR_PCH_2C5F0': 13, 'REYATR_PCH_4C1F2': 19,
                    'REYATR_PCH_4C5F0': 26, 'REYATR_RES_36C2F0': 8, starter.PNP_CELL: 9}
        self.assertEqual(Counter(p['cell'] for p in parts), expected)
        self.assertEqual(len({p['instance'] for p in parts}), 125)
        self.assertEqual(sum('xfill' in p['schematic_path'] for p in parts), 22)
        self.assertEqual(sum(p['schematic_path'].startswith('xcc<') for p in parts), 5)
        uses = re.findall(r'^use (\S+) (\S+)\ntransform 1 0 (-?\d+) 0 1 (-?\d+)\nbox (.+)$', body, re.M)
        actual = {(name, cell, x, y) for cell, name, x, y, box in uses}
        self.assertEqual(actual, {(p['instance'], p['cell'], p['x_units'], p['y_units']) for p in parts})
        self.assertEqual(re.findall(r'^<< (.+) >>$', body, re.M), ['labels', 'end'])
        self.assertEqual(body.count('\nport '), 11)
        rectangles = []
        for cell, name, x, y, box in uses:
            bounds = starter.painted_bounds(starter.ROOT/manifest['cells'][cell]['path'])
            self.assertEqual(list(map(int, box.split())), bounds)
            rectangles.append([bounds[0]+int(x), bounds[1]+int(y), bounds[2]+int(x), bounds[3]+int(y)])
        for a, b in itertools.combinations(rectangles, 2):
            self.assertGreaterEqual(max(b[0]-a[2], a[0]-b[2], b[1]-a[3], a[1]-b[3]), starter.GAP)
        width = max(b[2] for b in rectangles) - min(b[0] for b in rectangles)
        height = max(b[3] for b in rectangles) - min(b[1] for b in rectangles)
        self.assertLess(max(width, height) / min(width, height), 1.3)
        # The tile's nominal placement box is smaller than its actual well paint.
        self.assertEqual(starter.painted_bounds(starter.ROOT/'cells/REY_ATR_SKY130A/REYATR_PCH_4C5F0.mag'),
                         [-184, -128, 1784, 928])

    def test_taps_are_a_separate_palette(self):
        assets = starter.render()
        self.assertNotIn('TAP', assets['LELOTEMP_BIAS_IBP.mag'])
        uses = re.findall(r'^use (\S+) ', assets['tap_palette.mag'], re.M)
        self.assertEqual(len(uses), 10)
        self.assertEqual(len(set(uses)), 10)
        self.assertTrue(all('TAP' in name for name in uses))

    def test_nested_multiplicity_and_unsupported_constructs(self):
        definitions = starter.subcircuits('.subckt top a b\nX1 a b child\nX2 a b child\n.ends\n'
            '.subckt child a b\nXC a b tile\n.ends\n.subckt tile a b\n.ends\n')
        parts = starter.inventory(definitions, 'top', {'tile'})
        self.assertEqual({p['schematic_path'] for p in parts}, {'X1/XC', 'X2/XC'})
        for bad in ['X1 a b child m=2', 'X1 a b unknown', 'X1 a b top']:
            changed = dict(definitions, top=starter.subcircuits(f'.subckt top a b\n{bad}\n.ends')['top'])
            with self.assertRaises(ValueError):
                starter.inventory(changed, 'top', {'tile'})
        with self.assertRaises(ValueError):
            starter.subcircuits('.subckt top a b\nR1 a b 1k\n.ends')


if __name__ == '__main__':
    unittest.main()
