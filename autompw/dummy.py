from __future__ import annotations

from pathlib import Path

import klayout.db as kdb

from .calibre import CalibreTask, enabled_flows, run_calibre
from .config import DesignConfig, ProjectConfig
from .framework import (
    generate_blank_placeholder,
    generate_framework,
    mpw_dummy_output_path,
    mpw_dummy_work_base,
    placeholder_blank_path,
    placeholder_final_path,
    placeholder_output_base,
)
from .gds_io import get_top_cell, make_layout, read_layout, write_layout


def build_mpw_dummy_tasks(config: ProjectConfig) -> list[CalibreTask]:
    input_gds = config.resolve(config.output.framework_gds)
    tasks = []
    for flow_name, flow in enabled_flows(config).items():
        work_base = mpw_dummy_work_base(config, flow_name)
        output_gds = mpw_dummy_output_path(config, flow_name)
        tasks.append(
            CalibreTask(
                name=f"mpw_{flow_name}",
                flow_name=flow_name,
                flow=flow,
                input_gds=input_gds,
                input_topcell=config.topcell,
                output_gds=output_gds,
                summary_report=work_base / flow.summary_name,
                rendered_deck=work_base / f"{config.topcell}_{flow_name}.svrf",
                log_path=work_base / f"{config.topcell}_{flow_name}.log",
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
        output_gds = base / f"{design.name}_{flow_name}.gds"
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
        flow_outputs = []
        for task in build_placeholder_tasks(config, design):
            run_calibre(config, task, dry_run=dry_run)
            flow_outputs.append(task.output_gds)
        final = placeholder_final_path(config, design)
        if not dry_run:
            merge_placeholder_outputs(config, design, blank, flow_outputs, final)
        outputs.append(final)
    return outputs


def merge_placeholder_outputs(
    config: ProjectConfig,
    design: DesignConfig,
    marker_gds: Path,
    dummy_gds_files: list[Path],
    output_path: Path | None = None,
) -> Path:
    out = output_path or placeholder_final_path(config, design)
    layout = make_layout(config.gds.dbu_um)
    top = layout.create_cell(f"PLACEHOLDER_{design.name}")

    _insert_gds_at_origin(layout, top, marker_gds, f"MARKER_{design.name}", f"PLACEHOLDER_{design.name}")
    for path in dummy_gds_files:
        _insert_gds_at_origin(layout, top, path, f"DUMMY_{design.name}_{path.stem}", None)

    write_layout(layout, out)
    return out


def _insert_gds_at_origin(
    target_layout: kdb.Layout,
    target_top: kdb.Cell,
    source_path: Path,
    cell_name: str,
    source_topcell: str | None,
) -> None:
    source_layout = read_layout(source_path)
    if abs(source_layout.dbu - target_layout.dbu) > 1e-12:
        raise ValueError(f"DBU mismatch for {source_path}: {source_layout.dbu} vs {target_layout.dbu}")
    source_top = get_top_cell(source_layout, source_topcell)
    dest = target_layout.create_cell(_unique_cell_name(target_layout, cell_name))
    dest.copy_tree(source_top)
    target_top.insert(kdb.CellInstArray(dest.cell_index(), kdb.Trans()))


def _unique_cell_name(layout: kdb.Layout, base: str) -> str:
    if layout.cell(base) is None:
        return base
    i = 1
    while layout.cell(f"{base}_{i}") is not None:
        i += 1
    return f"{base}_{i}"
