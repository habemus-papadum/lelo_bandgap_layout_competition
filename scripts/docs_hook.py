"""Stage the existing Markdown and public assets without duplicating their sources."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def on_pre_build(config, **kwargs):
    destination = Path(config.docs_dir)
    sources = [ROOT / name for name in ("README.md", "competition.yaml", "tools.local.example.yaml", "pyproject.toml", "bandgap_cli.py", "project.py", "pdk_tools.py", "starter.py", "magicrc")]
    for name in ("docs", "LICENSES", "testbenches", "cells", "schematic", "reference", "templates", "tools", "tests"):
        sources.extend(p for p in (ROOT / name).rglob("*") if p.is_file()
                       and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".log"))
    expected = {destination / ".gitkeep"}
    for source in sources:
        relative = source.relative_to(ROOT)
        target = destination / ("index.md" if relative == Path("README.md") else relative)
        data = source.read_bytes()
        if source.suffix == ".md":
            data = data.replace(b"(../README.md", b"(../index.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
        expected.add(target)
    for stale in destination.rglob("*"):
        if stale.is_file() and stale not in expected:
            stale.unlink()
