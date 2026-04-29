from __future__ import annotations

import platform
import json
from pathlib import Path
from typing import Optional

import typer

import autompw
from .assemble import assemble as assemble_gds
from .config import load_config
from .dummy import run_mpw_dummy_fill, run_placeholders
from .framework import generate_framework
from .gds_io import inspect_gds
from .report import CheckItem, check_project_steps, run_check_step
from .templates import init_process

app = typer.Typer(no_args_is_help=True)
DEFAULT_CONFIG = Path("mpw_config.yaml")


@app.command()
def init(process: str = typer.Argument(...)) -> None:
    try:
        config = init_process(process, Path.cwd())
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(1)
    typer.echo(str(config))


@app.command()
def version() -> None:
    typer.echo(f"autompw {autompw.__version__}")
    typer.echo(f"python {platform.python_version()}")
    typer.echo(f"module {Path(autompw.__file__).resolve()}")


@app.command()
def check(
    config: Path = typer.Argument(DEFAULT_CONFIG),
    report: Optional[Path] = None,
    probe_calibre: bool = True,
) -> None:
    project = load_config(config)
    items = _run_check_steps(project, probe_calibre=probe_calibre)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps([_check_item_dict(item) for item in items], indent=2), encoding="utf-8")
    if any(item.severity == "error" for item in items):
        raise typer.Exit(1)


@app.command()
def framework(config: Path = typer.Argument(DEFAULT_CONFIG)) -> None:
    project = load_config(config)
    out = generate_framework(project)
    typer.echo(str(out))


@app.command("dummy-fill")
def dummy_fill(config: Path = typer.Argument(DEFAULT_CONFIG), dry_run: bool = False) -> None:
    project = load_config(config)
    outputs = run_mpw_dummy_fill(project, dry_run=dry_run)
    for output in outputs:
        typer.echo(str(output))


@app.command("placeholders")
def placeholders(config: Path = typer.Argument(DEFAULT_CONFIG), dry_run: bool = False) -> None:
    project = load_config(config)
    outputs = run_placeholders(project, dry_run=dry_run)
    for output in outputs:
        typer.echo(str(output))


@app.command()
def assemble(config: Path = typer.Argument(DEFAULT_CONFIG), strict_dummy: bool = True) -> None:
    project = load_config(config)
    out = assemble_gds(project, strict_dummy=strict_dummy, progress=typer.echo)
    typer.echo(str(out))


@app.command("all")
def run_all(config: Path = typer.Argument(DEFAULT_CONFIG), dry_run_calibre: bool = False) -> None:
    project = load_config(config)
    items = _run_check_steps(project, probe_calibre=not dry_run_calibre)
    if any(item.severity == "error" for item in items):
        raise typer.Exit(1)
    generate_framework(project)
    run_mpw_dummy_fill(project, dry_run=dry_run_calibre)
    run_placeholders(project, dry_run=dry_run_calibre)
    out = assemble_gds(project, strict_dummy=not dry_run_calibre, progress=typer.echo)
    typer.echo(str(out))


@app.command("inspect-gds")
def inspect(path: Path) -> None:
    typer.echo(json.dumps(inspect_gds(path), indent=2))


def _run_check_steps(project, probe_calibre: bool) -> list[CheckItem]:
    items = []
    for step in check_project_steps(project, probe_calibre=probe_calibre):
        typer.echo(f"[{step.name}] - CHECKING...")
        item = run_check_step(step)
        _echo_check_item(item)
        items.append(item)
    return items


def _echo_check_item(item: CheckItem) -> None:
    typer.echo(f"[{item.name}] - {item.severity.upper()}: {item.message}")
    for issue in item.issues:
        typer.echo(f"  - {issue.severity.upper()}: {issue.message}")


def _check_item_dict(item: CheckItem) -> dict[str, object]:
    return {
        "name": item.name,
        "severity": item.severity,
        "message": item.message,
        "issues": [issue.__dict__ for issue in item.issues],
    }


if __name__ == "__main__":
    app()
