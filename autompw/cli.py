from __future__ import annotations

import platform
import json
from pathlib import Path
from typing import Optional

import typer
import yaml

import autompw
from .assemble import assemble as assemble_gds
from .config import load_config
from .dummy import run_mpw_dummy_fill, run_placeholders
from .framework import generate_framework
from .gds_io import inspect_gds, write_gds_inspection_text
from .planner import apply_plan, generate_plan_report, plan_report_path, plan_summary_lines
from .preview import generate_preview
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
def inspect(path: Path, config: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c")) -> None:
    sram_prefixes = ()
    if config.exists():
        project = load_config(config)
        sram_prefixes = project.inspect.sram_prefixes
    text_report = write_gds_inspection_text(path, sram_prefixes=sram_prefixes)
    typer.echo(f"text report: {text_report}")
    typer.echo(json.dumps(inspect_gds(path), indent=2))


@app.command("plan")
def plan(
    config: Path = typer.Argument(DEFAULT_CONFIG),
    allow_rotation: bool = typer.Option(False, "--allow-rotation", help="Allow 90 degree clockwise chip rotation."),
) -> None:
    project = load_config(config)
    out = generate_plan_report(project, allow_rotation=allow_rotation)
    report = yaml.safe_load(out.read_text(encoding="utf-8"))
    typer.echo(f"plan report: {out}")
    _echo_plan_summary(report)


@app.command("preview")
def preview(
    config: Path = typer.Argument(DEFAULT_CONFIG),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Preview output directory."),
    basename: str = typer.Option("placement_preview", "--basename", help="Output filename stem."),
) -> None:
    project = load_config(config)
    result = generate_preview(project, output_dir=output_dir, basename=basename)
    typer.echo(f"preview svg: {result.svg_path}")
    typer.echo(f"preview html: {result.html_path}")
    typer.echo(f"preview png: {result.png_path}")
    typer.echo(f"utilization: {result.utilization_percent:.2f}%")
    if result.cuts:
        typer.echo(f"guillotine cuts: {len(result.cuts)}")
    else:
        typer.echo("guillotine cuts: not detected")
    if result.issues:
        typer.echo(f"issues: {len(result.issues)}")
        for issue in result.issues:
            typer.echo(f"  - {issue.severity.upper()} {issue.kind}: {issue.message}")
    else:
        typer.echo("issues: none")


@app.command("useplan")
def useplan(plan_number: int = typer.Argument(...), config: Path = typer.Argument(DEFAULT_CONFIG)) -> None:
    try:
        config_path, backup = apply_plan(config, plan_number, report_path=None)
    except ValueError as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(1)
    typer.echo(f"backup: {backup}")
    typer.echo(f"updated: {config_path}")
    project = load_config(config_path)
    typer.echo(f"plan report: {plan_report_path(project)}")


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


def _echo_plan_summary(report: dict[str, object]) -> None:
    for line in plan_summary_lines(report):
        typer.echo(line)


if __name__ == "__main__":
    app()
