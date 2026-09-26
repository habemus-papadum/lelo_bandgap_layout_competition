"""Project paths, local configuration, and directory-based submission metadata."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def local_settings():
    path = ROOT / 'tools.local.yaml'
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def project_path(value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def pdk_root(override=None):
    value = override or os.environ.get('BANDGAP_PDK_ROOT') or local_settings().get('pdk_root') or os.environ.get('PDK_ROOT')
    return project_path(value) if value else ROOT / 'pdk'


def select_submission(directory=None, reference=False):
    if directory is not None and reference:
        raise ValueError('Choose --submission or --reference, not both.')
    if directory is None and not reference:
        default = local_settings().get('default_submission')
        directory = project_path(default) if default else None
    config = yaml.safe_load((ROOT / 'competition.yaml').read_text())
    if directory is None:
        layout = ROOT / config['reference_layout']
        return layout.parent, layout, 'provided', True
    directory = Path(directory).expanduser().resolve()
    path = directory / 'submission.yaml'
    if not path.is_file():
        raise ValueError(f'Missing {path}; create an entry with bandgap new DIRECTORY --track provided|custom.')
    metadata = yaml.safe_load(path.read_text()) or {}
    if metadata.get('schema_version') != 1 or metadata.get('track') not in ('provided', 'custom'):
        raise ValueError(f'Invalid submission metadata: {path}')
    if metadata.get('layout') != config['top'] + '.mag':
        raise ValueError(f'Submission layout must be {config["top"]}.mag')
    return directory, directory / metadata['layout'], metadata['track'], False


def create_submission(directory, track):
    directory = Path(directory).expanduser().resolve()
    config = yaml.safe_load((ROOT / 'competition.yaml').read_text())
    directory.mkdir(parents=True, exist_ok=False)
    layout = config['top'] + '.mag'
    # Unattached labels provide an interface sketch, not fabricated geometry.
    lines = ['magic', 'tech sky130A', 'magscale 1 2', 'timestamp 0', '<< labels >>']
    for index, name in enumerate(config['ports'], 1):
        y = (index - 1) * 800
        lines += [f'rlabel space 0 {y} 0 {y} 0 {name}', f'port {index} nsew signal bidirectional']
    lines += ['<< end >>', '']
    (directory / layout).write_text('\n'.join(lines))
    (directory / 'submission.yaml').write_text(yaml.safe_dump({'schema_version': 1, 'track': track, 'layout': layout}, sort_keys=False))
    (directory / '.gitignore').write_text('runs/\n')
    return directory
