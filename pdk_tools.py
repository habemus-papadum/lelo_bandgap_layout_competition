"""Optional offline installation and byte comparisons for the bundled PDK."""
import hashlib
import json
import os
from pathlib import Path
import shutil

from project import ROOT


def cache_destination():
    base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')).expanduser()
    return base / 'lelo_bandgap_layout_competition' / 'pdk'


def inventory(directory):
    directory = Path(directory)
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for name in ('sky130A', 'scripts') for p in (directory / name).rglob('*') if p.is_file()}


def compare(directory):
    expected = json.loads((ROOT / 'pdk/manifest.json').read_text())['files']
    actual = inventory(directory)
    return {'matching': sum(actual.get(p) == h for p, h in expected.items()),
            'changed': sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p]),
            'missing': sorted(expected.keys() - actual.keys()),
            'extra': sorted(actual.keys() - expected.keys())}


def install(directory):
    directory = Path(directory).expanduser().resolve()
    if directory.exists():
        raise ValueError(f'Destination already exists: {directory}; it was not modified.')
    if directory.is_relative_to(ROOT / 'pdk'):
        raise ValueError('Destination must be outside the bundled PDK.')
    directory.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'pdk', directory, symlinks=True)
    result = compare(directory)
    if result['changed'] or result['missing'] or result['extra']:
        raise RuntimeError(f'PDK copy verification failed: {result}')
    return directory
