from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import ProjectConfig
from .gds_io import bbox_from_box, get_top_cell, read_layout


@dataclass(frozen=True)
class CheckIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class CheckItem:
    name: str
    severity: str
    message: str
    issues: tuple[CheckIssue, ...] = ()


def check_project(config: ProjectConfig, probe_calibre: bool = True) -> list[CheckIssue]:
    return [issue for item in check_project_items(config, probe_calibre=probe_calibre) for issue in item.issues]


def check_project_items(config: ProjectConfig, probe_calibre: bool = True) -> list[CheckItem]:
    items = [
        _item("geometry", check_geometry(config), "placement geometry is valid"),
        _item("design_gds", check_design_gds(config), "design GDS files are readable and match configured metadata"),
        _item("calibre_decks", check_calibre_decks(config), "Calibre deck templates are present and recognizable"),
    ]
    if probe_calibre:
        items.append(_item("calibre_command", check_calibre_command(config), "Calibre command starts successfully"))
    else:
        items.append(CheckItem("calibre_command", "warning", "Calibre command probe skipped"))
    return items


def _item(name: str, issues: list[CheckIssue], ok_message: str) -> CheckItem:
    if any(issue.severity == "error" for issue in issues):
        severity = "error"
    elif any(issue.severity == "warning" for issue in issues):
        severity = "warning"
    else:
        severity = "ok"
    message = ok_message if severity == "ok" else f"{len(issues)} issue(s)"
    return CheckItem(name, severity, message, tuple(issues))


def check_geometry(config: ProjectConfig) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    mpw_bbox = config.mpw.bbox

    for design in config.designs:
        bbox = design.bbox
        if not mpw_bbox.contains(bbox):
            issues.append(
                CheckIssue(
                    "error",
                    f"{design.name} bbox {bbox.as_list()} is outside MPW bbox {mpw_bbox.as_list()}",
                )
            )

    for i, left in enumerate(config.designs):
        for right in config.designs[i + 1 :]:
            left_bbox = left.bbox
            right_bbox = right.bbox
            if left_bbox.overlaps(right_bbox):
                issues.append(
                    CheckIssue(
                        "error",
                        f"{left.name} bbox {left_bbox.as_list()} overlaps {right.name} bbox {right_bbox.as_list()}",
                    )
                )
                continue
            spacing = left_bbox.spacing_to(right_bbox)
            if spacing < config.spacing_design_to_design_um:
                issues.append(
                    CheckIssue(
                        "error",
                        f"{left.name} to {right.name} spacing {spacing:.3f}um is below {config.spacing_design_to_design_um:.3f}um",
                    )
                )

    return issues


def check_design_gds(config: ProjectConfig, tolerance_um: float = 0.001) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    for design in config.designs:
        path = config.resolve(design.gds)
        if not path.exists():
            severity = "warning" if design.replace_with_placeholder else "error"
            issues.append(CheckIssue(severity, f"{design.name} GDS does not exist: {path}"))
            continue
        try:
            layout = read_layout(path)
            top = get_top_cell(layout, design.topcell)
        except Exception as exc:
            severity = "warning" if design.replace_with_placeholder else "error"
            issues.append(CheckIssue(severity, f"{design.name} GDS cannot be read: {path}: {exc}"))
            continue

        bbox = top.bbox()
        if bbox.empty():
            issues.append(CheckIssue("warning", f"{design.name} topcell bbox is empty: {path}"))
            continue
        bbox_um = bbox_from_box(bbox, layout.dbu)
        if abs(bbox_um.xmin - design.bottom_left[0]) > tolerance_um or abs(bbox_um.ymin - design.bottom_left[1]) > tolerance_um:
            issues.append(
                CheckIssue(
                    "warning",
                    f"{design.name} GDS bbox lower-left {bbox_um.as_list()[:2]} does not match configured bottom_left {list(design.bottom_left)}",
                )
            )
        width = bbox_um.xmax - bbox_um.xmin
        height = bbox_um.ymax - bbox_um.ymin
        if abs(width - design.size_um[0]) > tolerance_um or abs(height - design.size_um[1]) > tolerance_um:
            issues.append(
                CheckIssue(
                    "warning",
                    f"{design.name} GDS bbox size [{width:.3f}, {height:.3f}]um does not match configured size_um {list(design.size_um)}",
                )
            )
    return issues


def check_calibre_decks(config: ProjectConfig) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    for name, flow in config.calibre.flows.items():
        if not flow.enabled:
            continue
        path = config.resolve(flow.deck_template)
        if not path.exists():
            issues.append(CheckIssue("error", f"Calibre flow {name} deck_template does not exist: {path}"))
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            issues.append(CheckIssue("error", f"Calibre flow {name} deck_template cannot be read: {path}: {exc}"))
            continue
        missing = [
            field
            for field in (
                "LAYOUT PATH",
                "LAYOUT PRIMARY",
                "DRC SUMMARY REPORT",
                "VARIABLE xLB",
                "VARIABLE yLB",
                "VARIABLE xRT",
                "VARIABLE yRT",
            )
            if field not in text
        ]
        has_output = "DRC RESULTS DATABASE" in text or "DFM DEFAULTS RDB GDS FILE" in text
        if missing or not has_output:
            parts = missing + ([] if has_output else ["DRC RESULTS DATABASE or DFM DEFAULTS RDB GDS FILE"])
            issues.append(
                CheckIssue(
                    "warning",
                    f"Calibre flow {name} deck_template may not be recognized for automatic rendering; missing: {', '.join(parts)}",
                )
            )
    if not config.calibre.flows:
        issues.append(CheckIssue("warning", "No Calibre flows are configured"))
    return issues


def check_calibre_command(config: ProjectConfig, timeout_s: int = 20) -> list[CheckIssue]:
    command = f"{shlex.quote(config.calibre.executable)} -version"
    if config.calibre.setup_script:
        command = f"source {shlex.quote(config.calibre.setup_script)}; {command}"
        setup_path = Path(config.calibre.setup_script)
        if not setup_path.exists():
            return [CheckIssue("error", f"Calibre setup_script does not exist on this machine: {setup_path}")]
    if config.calibre.shell:
        shell_name = Path(config.calibre.shell).name
        shell_flag = "-c" if shell_name in {"csh", "tcsh"} else "-lc"
        shell_command = [config.calibre.shell, shell_flag, command]
    else:
        shell_command = ["/bin/sh", "-lc", command]
    try:
        result = subprocess.run(shell_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_s, check=False)
    except FileNotFoundError as exc:
        return [CheckIssue("error", f"Calibre shell or executable cannot be started: {exc}")]
    except subprocess.TimeoutExpired:
        return [CheckIssue("error", f"Calibre probe timed out after {timeout_s}s: {command}")]
    if result.returncode != 0:
        first_line = (result.stdout or "").strip().splitlines()
        detail = f": {first_line[0]}" if first_line else ""
        return [CheckIssue("error", f"Calibre probe command failed with code {result.returncode}{detail}")]
    return []
