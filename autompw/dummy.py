from __future__ import annotations

from pathlib import Path

from .calibre import CalibreTask, enabled_flows, run_calibre
from .config import DesignConfig, ProjectConfig
from .framework import (
    generate_blank_placeholder,
    generate_framework,
    mpw_dummy_output_base,
    placeholder_blank_path,
    placeholder_output_base,
)


def build_mpw_dummy_tasks(config: ProjectConfig) -> list[CalibreTask]:
    input_gds = config.resolve(config.output.framework_gds)
    tasks = []
    for flow_name, flow in enabled_flows(config).items():
        base = mpw_dummy_output_base(config, flow_name)
        output_gds = base / f"{config.topcell}{flow.output_suffix}.gds"
        tasks.append(
            CalibreTask(
                name=f"mpw_{flow_name}",
                flow_name=flow_name,
                flow=flow,
                input_gds=input_gds,
                input_topcell=config.topcell,
                output_gds=output_gds,
                summary_report=base / flow.summary_name,
                rendered_deck=base / f"{config.topcell}_{flow_name}.svrf",
                log_path=base / f"{config.topcell}_{flow_name}.log",
                width_um=config.mpw.size_um[0],
                height_um=config.mpw.size_um[1],
                x0_um=config.mpw.origin[0],
                y0_um=config.mpw.origin[1],
            )
        )
    return tasks


def build_placeholder_tasks(config: ProjectConfig, design: DesignConfig) -> list[CalibreTask]:
    input_gds = placeholder_blank_path(config, design)
    topcell = f"PLACEHOLDER_{design.name}"
    tasks = []
    for flow_name, flow in enabled_flows(config).items():
        base = placeholder_output_base(config, design, flow_name)
        output_gds = base / f"{design.name}{flow.output_suffix}.gds"
        tasks.append(
            CalibreTask(
                name=f"{design.name}_{flow_name}",
                flow_name=flow_name,
                flow=flow,
                input_gds=input_gds,
                input_topcell=topcell,
                output_gds=output_gds,
                summary_report=base / flow.summary_name,
                rendered_deck=base / f"{design.name}_{flow_name}.svrf",
                log_path=base / f"{design.name}_{flow_name}.log",
                width_um=design.size_um[0],
                height_um=design.size_um[1],
            )
        )
    return tasks


def run_mpw_dummy_fill(config: ProjectConfig, dry_run: bool = False) -> list[Path]:
    framework = config.resolve(config.output.framework_gds)
    if not framework.exists():
        generate_framework(config, framework)
    outputs = []
    for task in build_mpw_dummy_tasks(config):
        run_calibre(config, task, dry_run=dry_run)
        outputs.append(task.output_gds)
    return outputs


def run_placeholders(config: ProjectConfig, dry_run: bool = False) -> list[Path]:
    outputs = []
    for design in config.designs:
        blank = placeholder_blank_path(config, design)
        generate_blank_placeholder(config, design, blank)
        for task in build_placeholder_tasks(config, design):
            run_calibre(config, task, dry_run=dry_run)
            outputs.append(task.output_gds)
    return outputs
