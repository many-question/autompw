from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import CalibreFlowConfig, ProjectConfig


@dataclass(frozen=True)
class CalibreTask:
    name: str
    flow_name: str
    flow: CalibreFlowConfig
    input_gds: Path
    input_topcell: str
    output_gds: Path
    summary_report: Path
    rendered_deck: Path
    log_path: Path
    width_um: float
    height_um: float
    x0_um: float = 0.0
    y0_um: float = 0.0

    @property
    def x1_um(self) -> float:
        return self.x0_um + self.width_um

    @property
    def y1_um(self) -> float:
        return self.y0_um + self.height_um


def enabled_flows(config: ProjectConfig) -> dict[str, CalibreFlowConfig]:
    return {name: flow for name, flow in config.calibre.flows.items() if flow.enabled}


def render_deck(config: ProjectConfig, task: CalibreTask) -> Path:
    template_path = config.resolve(task.flow.deck_template)
    text = template_path.read_text(encoding="utf-8", errors="ignore")
    replacements = {
        "input_gds": str(task.input_gds),
        "input_topcell": task.input_topcell,
        "output_gds": str(task.output_gds),
        "summary_report": str(task.summary_report),
        "xLB": _fmt(task.x0_um),
        "yLB": _fmt(task.y0_um),
        "xRT": _fmt(task.x1_um),
        "yRT": _fmt(task.y1_um),
    }
    for key, value in replacements.items():
        text = text.replace("{{ " + key + " }}", value).replace("{{" + key + "}}", value)

    text = _replace_svrf_header(text, replacements)
    task.rendered_deck.parent.mkdir(parents=True, exist_ok=True)
    task.rendered_deck.write_text(text, encoding="utf-8")
    return task.rendered_deck


def run_calibre(config: ProjectConfig, task: CalibreTask, dry_run: bool = False) -> subprocess.CompletedProcess[str] | None:
    render_deck(config, task)
    task.output_gds.parent.mkdir(parents=True, exist_ok=True)
    task.summary_report.parent.mkdir(parents=True, exist_ok=True)
    task.log_path.parent.mkdir(parents=True, exist_ok=True)

    command = f"{config.calibre.executable} {config.calibre.args} {shlex.quote(str(task.rendered_deck))}"
    if config.calibre.setup_script:
        command = f"source {shlex.quote(config.calibre.setup_script)}; {command}"
    if dry_run:
        task.log_path.write_text(command + "\n", encoding="utf-8")
        return None

    if config.calibre.shell:
        shell_name = Path(config.calibre.shell).name
        shell_flag = "-c" if shell_name in {"csh", "tcsh"} else "-lc"
        shell_command = [config.calibre.shell, shell_flag, command]
    else:
        shell_command = ["/bin/sh", "-lc", command]
    result = subprocess.run(shell_command, text=True, capture_output=True, check=False)
    task.log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Calibre task {task.name} failed with code {result.returncode}. See {task.log_path}")
    if not task.output_gds.exists():
        raise FileNotFoundError(f"Calibre task {task.name} did not create {task.output_gds}")
    return result


def _replace_svrf_header(text: str, values: dict[str, str]) -> str:
    text = re.sub(
        r'(?m)^(\s*LAYOUT\s+PATH\s+)"[^"]*"(.*)$',
        lambda m: f'{m.group(1)}"{values["input_gds"]}"{m.group(2)}',
        text,
    )
    text = re.sub(
        r'(?m)^(\s*LAYOUT\s+PRIMARY\s+)"[^"]*"(.*)$',
        lambda m: f'{m.group(1)}"{values["input_topcell"]}"{m.group(2)}',
        text,
    )
    text = re.sub(
        r'(?m)^(\s*DRC\s+RESULTS\s+DATABASE\s+)"[^"]*"(\s+GDSII\b.*)$',
        lambda m: f'{m.group(1)}"{values["output_gds"]}"{m.group(2)}',
        text,
    )
    text = re.sub(
        r'(?m)^(\s*DFM\s+DEFAULTS\s+RDB\s+GDS\s+FILE\s+)"[^"]*"(.*)$',
        lambda m: f'{m.group(1)}"{values["output_gds"]}"{m.group(2)}',
        text,
    )
    text = re.sub(
        r'(?m)^(\s*DRC\s+SUMMARY\s+REPORT\s+)"[^"]*"(.*)$',
        lambda m: f'{m.group(1)}"{values["summary_report"]}"{m.group(2)}',
        text,
    )
    for var in ("xLB", "yLB", "xRT", "yRT"):
        text = re.sub(
            rf"(?m)^(\s*VARIABLE\s+{var}\s+)[^\s/]+(.*)$",
            lambda m, name=var: f"{m.group(1)}{values[name]}{m.group(2)}",
            text,
        )
    return text


def _fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
