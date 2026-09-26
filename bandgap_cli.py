"""Thin, discoverable CLI; numerical and physical checks remain in tools/."""
from enum import Enum
from pathlib import Path
import subprocess
import sys
from typing import Annotated

import typer

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


def run(script: str, arguments: list[str]) -> None:
    """Use the uv environment's interpreter and preserve tool failure exit codes."""
    raise typer.Exit(subprocess.call([sys.executable, str(ROOT / script), *arguments]))


def register_check(name: str, description: str) -> None:
    def command(
        layout: Annotated[Path | None, typer.Option(help="Top Magic file; defaults to the reference.")] = None,
        out: Annotated[Path, typer.Option(help="Reports and retained artifacts; reuse between dependent checks.")] = ROOT / "runs/reference",
        track: Annotated[Track, typer.Option(help="Provided tiles or custom device geometry.")] = Track.provided,
        mode: Annotated[Mode, typer.Option(help="Distributed RC, or C-only development extraction.")] = Mode.rc,
        profile: Annotated[Profile, typer.Option(help="Simulation/scoring grid: one or 45 conditions per view.")] = Profile.typical,
        view: Annotated[View, typer.Option(help="Circuit view for simulate; all runs both views.")] = View.schematic,
        analysis: Annotated[list[Analysis] | None, typer.Option(help="Simulate only: dc, tran, stability; repeat to combine. Default: all three.")] = None,
    ) -> None:
        if analysis and name != "simulate":
            raise typer.BadParameter("--analysis is only for simulate; all/scoring require every analysis.")
        args = [name, "--out", str(out), "--track", track.value, "--mode", mode.value,
                "--profile", profile.value, "--view", view.value]
        if layout is not None:
            args += ["--layout", str(layout)]
        for item in analysis or []:
            args += ["--analysis", item.value]
        run("tools/check.py", args)
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
    pdk_root: Annotated[Path | None, typer.Option(envvar="PDK_ROOT", help="Directory containing sky130A.")] = None,
    xschem: Annotated[str, typer.Option(help="Xschem executable or absolute path.")] = "xschem",
    output_dir: Annotated[Path, typer.Option(help="Generated views; canonical schematic files are not overwritten.")] = ROOT / "runs/netlist",
) -> None:
    """Regenerate both schematic SPICE views with Xschem."""
    args = ["--xschem", xschem, "--output-dir", str(output_dir)]
    if pdk_root is not None:
        args += ["--pdk-root", str(pdk_root)]
    run("schematic/netlist.py", args)


@app.command()
def acceptance(keep: Annotated[bool, typer.Option(help="Retain successful scratch directories too.")] = False) -> None:
    """Exercise 16 positive/negative evaluator checks; requires the EDA tools."""
    run("tests/acceptance.py", ["--keep"] if keep else [])


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
