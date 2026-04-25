from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from .assemble import assemble as assemble_gds
from .config import load_config
from .dummy import run_mpw_dummy_fill, run_placeholders
from .framework import generate_framework
from .gds_io import inspect_gds
from .report import check_project
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
def check(config: Path = typer.Argument(DEFAULT_CONFIG), report: Optional[Path] = None) -> None:
    project = load_config(config)
    issues = check_project(project)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps([issue.__dict__ for issue in issues], indent=2), encoding="utf-8")
    if issues:
        for issue in issues:
            typer.echo(f"{issue.severity.upper()}: {issue.message}")
        raise typer.Exit(1)
    typer.echo("OK: placement check passed")


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
    out = assemble_gds(project, strict_dummy=strict_dummy)
    typer.echo(str(out))


@app.command("all")
def run_all(config: Path = typer.Argument(DEFAULT_CONFIG), dry_run_calibre: bool = False) -> None:
    project = load_config(config)
    issues = check_project(project)
    if issues:
        for issue in issues:
            typer.echo(f"{issue.severity.upper()}: {issue.message}")
        raise typer.Exit(1)
    generate_framework(project)
    run_mpw_dummy_fill(project, dry_run=dry_run_calibre)
    run_placeholders(project, dry_run=dry_run_calibre)
    out = assemble_gds(project, strict_dummy=not dry_run_calibre)
    typer.echo(str(out))


@app.command("inspect-gds")
def inspect(path: Path) -> None:
    typer.echo(json.dumps(inspect_gds(path), indent=2))


if __name__ == "__main__":
    app()
