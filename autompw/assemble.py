from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import klayout.db as kdb

from .config import DesignConfig, ProjectConfig
from .dummy import build_mpw_dummy_tasks
from .framework import placeholder_final_path
from .gds_io import dbu_to_iu, get_top_cell, make_layout, read_layout, write_layout


def assemble(config: ProjectConfig, output_path: Path | None = None, strict_dummy: bool = True) -> Path:
    out = output_path or config.resolve(config.output.final_gds)
    layout = make_layout(config.gds.dbu_um)
    top = layout.create_cell(config.topcell)
    manifest: dict[str, object] = {"topcell": config.topcell, "placements": []}

    framework = config.resolve(config.output.framework_gds)
    if framework.exists():
        _add_gds_reference(layout, top, framework, config.topcell, 0.0, 0.0, f"FW_{config.topcell}", config)

    for task in build_mpw_dummy_tasks(config):
        if task.output_gds.exists():
            _add_gds_reference(layout, top, task.output_gds, None, 0.0, 0.0, f"DUMMYFILL_{task.flow_name}", config)

    for design in config.designs:
        source, topcell, source_bottom_left = _design_source(config, design, strict_dummy)
        bbox = design.bbox
        _add_gds_reference(
            layout,
            top,
            source,
            topcell,
            bbox.xmin,
            bbox.ymin,
            f"DESIGN_{design.name}",
            config,
            source_bottom_left,
        )
        manifest["placements"].append(
            {
                "name": design.name,
                "source": str(source),
                "topcell": topcell,
                "placed_bbox_um": bbox.as_list(),
                "source_bottom_left_um": list(source_bottom_left),
                "replaced_with_placeholder": design.replace_with_placeholder,
            }
        )

    if config.gds.flatten_final:
        top.flatten(True)
    write_layout(layout, out)
    manifest_path = out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


def _design_source(config: ProjectConfig, design: DesignConfig, strict_dummy: bool) -> tuple[Path, str | None, tuple[float, float]]:
    if not design.replace_with_placeholder:
        return config.resolve(design.gds), design.topcell, design.bottom_left

    placeholder = placeholder_final_path(config, design)
    if placeholder.exists():
        return placeholder, None, (0.0, 0.0)
    if strict_dummy:
        raise FileNotFoundError(f"No placeholder GDS found for {design.name}: {placeholder}")
    return config.resolve(design.gds), design.topcell, design.bottom_left


def _add_gds_reference(
    target_layout: kdb.Layout,
    target_top: kdb.Cell,
    source_path: Path,
    source_topcell: str | None,
    target_xmin_um: float,
    target_ymin_um: float,
    cell_name: str,
    config: ProjectConfig,
    source_bottom_left_um: tuple[float, float] | None = None,
) -> None:
    source_layout = read_layout(source_path)
    if abs(source_layout.dbu - target_layout.dbu) > 1e-12:
        raise ValueError(f"DBU mismatch for {source_path}: {source_layout.dbu} vs {target_layout.dbu}")
    source_top = get_top_cell(source_layout, source_topcell)
    dest = target_layout.create_cell(_unique_cell_name(target_layout, cell_name))
    dest.copy_tree(source_top)
    bbox = dest.bbox()
    if source_bottom_left_um is None:
        source_left = bbox.left
        source_bottom = bbox.bottom
    else:
        source_left = dbu_to_iu(source_bottom_left_um[0], target_layout.dbu)
        source_bottom = dbu_to_iu(source_bottom_left_um[1], target_layout.dbu)
    dx = dbu_to_iu(target_xmin_um, target_layout.dbu) - source_left
    dy = dbu_to_iu(target_ymin_um, target_layout.dbu) - source_bottom
    target_top.insert(kdb.CellInstArray(dest.cell_index(), kdb.Trans(dx, dy)))


def _unique_cell_name(layout: kdb.Layout, base: str) -> str:
    if layout.cell(base) is None:
        return base
    i = 1
    while layout.cell(f"{base}_{i}") is not None:
        i += 1
    return f"{base}_{i}"
