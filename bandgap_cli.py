"""Thin, discoverable CLI; numerical and physical checks remain in tools/."""
from enum import Enum
from pathlib import Path
import os
import shlex
import json
import subprocess
import sys
from typing import Annotated

import typer
import project
import pdk_tools

ROOT = Path(__file__).resolve().parent
app = typer.Typer(help="Sky130 bandgap layout competition: inspect, check, simulate and score.",
                  no_args_is_help=True, add_completion=False)


class Track(str, Enum):
    provided = "provided"
    custom = "custom"


class Mode(str, Enum):
    rc = "rc"
    c = "c"


class Profile(str, Enum):
    typical = "typical"
    corners = "corners"


class View(str, Enum):
    schematic = "schematic"
    layout = "layout"


class Analysis(str, Enum):
    dc = "dc"
    tran = "tran"
    stability = "stability"


def run(script: str, arguments: list[str], pdk=None) -> None:
    """Use the uv environment's interpreter and preserve tool failure exit codes."""
    selected = project.pdk_root(pdk)
    env = dict(os.environ, PDK_ROOT=str(selected), BANDGAP_PDK_ROOT=str(selected))
    raise typer.Exit(subprocess.call([sys.executable, str(ROOT / script), *arguments], env=env))


def register_check(name: str, description: str) -> None:
    def command(
        submission: Annotated[Path | None, typer.Option("--submission", "-s", help="Submission directory containing submission.yaml.")] = None,
        reference: Annotated[bool, typer.Option(help="Use the supplied reference, overriding the local default.")] = False,
        pdk_root: Annotated[Path | None, typer.Option(help="Override the PDK directory containing sky130A.")] = None,
        out: Annotated[Path | None, typer.Option(help="Override reports directory; normally isolated by submission/mode/profile.")] = None,
        mode: Annotated[Mode, typer.Option(help="Distributed RC, or C-only development extraction.")] = Mode.rc,
        profile: Annotated[Profile, typer.Option(help="Simulation/scoring grid: one or 45 conditions per view.")] = Profile.typical,
        view: Annotated[View, typer.Option(help="Circuit view for simulate; all runs both views.")] = View.schematic,
        analysis: Annotated[list[Analysis] | None, typer.Option(help="Simulate only: dc, tran, stability; repeat to combine. Default: all three.")] = None,
    ) -> None:
        if analysis and name != "simulate":
            raise typer.BadParameter("--analysis is only for simulate; all/scoring require every analysis.")
        try:
            directory, layout, track, is_reference = project.select_submission(submission, reference)
        except (ValueError, OSError) as exc:
            raise typer.BadParameter(str(exc)) from exc
        if out is None:
            base = ROOT / "runs/reference" if is_reference else directory / "runs"
            out = base / mode.value / profile.value
        selected_pdk = project.pdk_root(pdk_root)
        typer.echo(f"{'Reference' if is_reference else 'Submission'}: {directory}\n"
                   f"Track: {track} | PDK: {selected_pdk}\nReports: {out.resolve()}", err=True)
        args = [name, "--layout", str(layout), "--out", str(out), "--track", track,
                "--mode", mode.value, "--profile", profile.value, "--view", view.value]
        for item in analysis or []:
            args += ["--analysis", item.value]
        run("tools/check.py", args, selected_pdk)

    app.command(name, help=description)(command)


for name, description in {
    "doctor": "Check installed EDA tools, complete hierarchy and a real PDK model.",
    "drc": "Require zero violations from Magic's full Sky130A DRC deck.",
    "lvs": "Extract connectivity and require a unique schematic match.",
    "area": "Measure the bounding area of flattened physical paint.",
    "extract": "Export parasitics and verify contracted connectivity with LVS.",
    "simulate": "Run DC, startup/shutdown and loop stability for a selected view.",
    "score": "Validate prerequisite reports and compute the published score.",
    "all": "Run every check, simulate both views, and score. Typical is about 2 minutes.",
}.items():
    register_check(name, description)


@app.command()
def netlist(
    pdk_root: Annotated[Path | None, typer.Option(help="Directory containing sky130A; defaults to configured/bundled PDK.")] = None,
    xschem: Annotated[str, typer.Option(help="Xschem executable or absolute path.")] = "xschem",
    output_dir: Annotated[Path, typer.Option(help="Generated views; canonical schematic files are not overwritten.")] = ROOT / "runs/netlist",
) -> None:
    """Regenerate both schematic SPICE views with Xschem."""
    args = ["--xschem", xschem, "--output-dir", str(output_dir)]
    selected = project.pdk_root(pdk_root)
    typer.echo(f"Schematic: {ROOT / 'schematic'} | PDK: {selected}", err=True)
    args += ["--pdk-root", str(selected)]
    run("schematic/netlist.py", args, selected)


@app.command()
def acceptance(keep: Annotated[bool, typer.Option(help="Retain successful scratch directories too.")] = False) -> None:
    """Exercise positive/negative evaluator checks; requires the EDA tools."""
    typer.echo(f"Acceptance fixtures: disposable copies of {ROOT} | PDK: {project.pdk_root()}", err=True)
    run("tests/acceptance.py", ["--keep"] if keep else [])


@app.command("new")
def new_submission(
    directory: Annotated[Path, typer.Argument(help="New submission directory; must not already exist.")],
    track: Annotated[Track, typer.Option(help="Fixed-cell assembly or custom device layout.")],
) -> None:
    """Create an empty layout with pin labels and track metadata (no reference geometry)."""
    try:
        created = project.create_submission(directory, track.value)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Created {created} | Track: {track.value}\nPin-only starter: layout checks intentionally fail until geometry is added.")


@app.command("env")
def environment(pdk_root: Annotated[Path | None, typer.Option(help="PDK override for direct tool use.")] = None) -> None:
    """Print shell-quoted exports for use with eval; no tool installation required."""
    for key, value in {"PDK_ROOT": project.pdk_root(pdk_root), "BANDGAP_ROOT": ROOT}.items():
        typer.echo(f"export {key}={shlex.quote(str(value))}")


pdk_app = typer.Typer(help="Inspect or copy the bundled PDK; no download or recursive clone needed.", no_args_is_help=True)
app.add_typer(pdk_app, name="pdk")


@pdk_app.command("path")
def pdk_path() -> None:
    """Print the effective PDK directory (local config/environment override the bundle)."""
    typer.echo(project.pdk_root())


@pdk_app.command("install")
def pdk_install(directory: Annotated[Path | None, typer.Argument(help="Copy destination; defaults to the competition's XDG cache directory.")] = None) -> None:
    """Copy and verify the complete bundle to another location, without network access."""
    try:
        destination = pdk_tools.install(directory or pdk_tools.cache_destination())
    except (ValueError, OSError, RuntimeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Installed PDK: {destination}\nUse --pdk-root {shlex.quote(str(destination))} or configure pdk_root in tools.local.yaml.")


@pdk_app.command("compare")
def pdk_compare(directory: Annotated[Path, typer.Argument(help="PDK root to compare against the bundled snapshot.")]) -> None:
    """Report matching, changed, missing and extra files as JSON."""
    result = pdk_tools.compare(directory.expanduser().resolve())
    typer.echo(json.dumps(result, indent=2))
    if result['changed'] or result['missing'] or result['extra']:
        raise typer.Exit(1)


@app.command("help")
def help_command(ctx: typer.Context, command: Annotated[str | None, typer.Argument(help="Optional command name.")] = None) -> None:
    """Show general help or help for a particular command (also --help)."""
    parent = ctx.parent
    if command is None:
        typer.echo(parent.get_help())
        return
    selected = parent.command.get_command(parent, command)
    if selected is None:
        raise typer.BadParameter(f"Unknown command: {command}")
    with typer.Context(selected, info_name=command, parent=parent) as child:
        typer.echo(selected.get_help(child))


if __name__ == "__main__":
    app()
