"""Project paths, local configuration, and directory-based submission metadata."""
import os
from pathlib import Path
import shutil

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


def select_magic_layout(target=None, submission=None, reference=False):
    """Resolve an editor target, including raw template directories and blank entries."""
    if sum((target is not None, submission is not None, reference)) > 1:
        raise ValueError('Choose a layout path, --submission, or --reference, not more than one.')
    if target is None:
        _, layout, _, _ = select_submission(submission, reference)
    else:
        layout = Path(target).expanduser().resolve()
        if layout.is_dir():
            if (layout / 'submission.yaml').is_file():
                _, layout, _, _ = select_submission(layout)
            else:
                config = yaml.safe_load((ROOT / 'competition.yaml').read_text())
                layout /= config['top'] + '.mag'
    if layout.suffix != '.mag' or not layout.is_file():
        raise ValueError(f'Missing Magic layout (.mag file): {layout}')
    return layout


def create_submission(directory, track):
    directory = Path(directory).expanduser().resolve()
    if track not in ('provided', 'custom'):
        raise ValueError(f'Unknown track: {track}')
    config = yaml.safe_load((ROOT / 'competition.yaml').read_text())
    directory.mkdir(parents=True, exist_ok=False)
    layout = config['top'] + '.mag'
    if track == 'provided':
        for name in (layout, 'tap_palette.mag', 'inventory.csv', 'provenance.json', 'README.md'):
            shutil.copyfile(ROOT / 'templates/provided' / name, directory / name)
    else:
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
