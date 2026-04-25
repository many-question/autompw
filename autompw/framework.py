from __future__ import annotations

from pathlib import Path

import klayout.db as kdb

from .config import DesignConfig, ProjectConfig
from .gds_io import box_from_bbox, dbu_to_iu, layer_index, make_layout, write_layout
from .geometry import BBox


def generate_framework(config: ProjectConfig, output_path: Path | None = None) -> Path:
    out = output_path or config.resolve(config.output.framework_gds)
    layout = make_layout(config.gds.dbu_um)
    top = layout.create_cell(config.topcell)

    marker_layer = layer_index(layout, config.layers.marker)
    top.shapes(marker_layer).insert(box_from_bbox(config.mpw.bbox, layout.dbu))
    for design in config.designs:
        _insert_design_markers(layout, top, design, marker_layer, config, config.mpw.bbox)

    write_layout(layout, out)
    return out


def generate_blank_blocker(config: ProjectConfig, design: DesignConfig, output_path: Path) -> Path:
    layout = make_layout(config.gds.dbu_um)
    top = layout.create_cell(f"DUMMY_{design.name}")
    local_bbox = BBox(0.0, 0.0, design.size_um[0], design.size_um[1])
    marker_layer = layer_index(layout, config.layers.marker)
    top.shapes(marker_layer).insert(box_from_bbox(local_bbox, layout.dbu))

    _insert_blocker_layers(layout, top, local_bbox, config, local_bbox)
    _insert_edge_layers(layout, top, local_bbox, config, local_bbox)
    write_layout(layout, output_path)
    return output_path


def _insert_design_markers(
    layout: kdb.Layout,
    top: kdb.Cell,
    design: DesignConfig,
    marker_layer: int,
    config: ProjectConfig,
    clip_bbox: BBox,
) -> None:
    bbox = design.bbox
    top.shapes(marker_layer).insert(box_from_bbox(bbox, layout.dbu))
    _insert_blocker_layers(layout, top, bbox, config, clip_bbox)
    _insert_edge_layers(layout, top, bbox, config, clip_bbox)


def _insert_blocker_layers(
    layout: kdb.Layout,
    top: kdb.Cell,
    bbox: BBox,
    config: ProjectConfig,
    clip_bbox: BBox,
) -> None:
    clip_region = kdb.Region(box_from_bbox(clip_bbox, layout.dbu))
    for blocker in config.layers.dummy_blocker:
        grow = blocker.grow_um
        grown = BBox(bbox.xmin - grow, bbox.ymin - grow, bbox.xmax + grow, bbox.ymax + grow)
        clipped = kdb.Region(box_from_bbox(grown, layout.dbu)) & clip_region
        if not clipped.is_empty():
            top.shapes(layer_index(layout, blocker.layer)).insert(clipped)


def _insert_edge_layers(
    layout: kdb.Layout,
    top: kdb.Cell,
    bbox: BBox,
    config: ProjectConfig,
    clip_bbox: BBox,
) -> None:
    if not config.layers.edge_fill_layers:
        return
    width = config.layers.edge_fill_width_um
    outer = box_from_bbox(BBox(bbox.xmin - width, bbox.ymin - width, bbox.xmax + width, bbox.ymax + width), layout.dbu)
    inner = box_from_bbox(bbox, layout.dbu)
    ring = (kdb.Region(outer) - kdb.Region(inner)) & kdb.Region(box_from_bbox(clip_bbox, layout.dbu))
    if ring.is_empty():
        return
    for layer in config.layers.edge_fill_layers:
        top.shapes(layer_index(layout, layer)).insert(ring)


def blocker_blank_path(config: ProjectConfig, design: DesignConfig) -> Path:
    return config.resolve(config.output.build_dir) / "dummy_blockers" / f"{design.name}_blank.gds"


def blocker_output_base(config: ProjectConfig, design: DesignConfig, flow_name: str) -> Path:
    return config.resolve(config.calibre.work_dir) / "dummy_blockers" / design.name / flow_name


def mpw_dummy_output_base(config: ProjectConfig, flow_name: str) -> Path:
    return config.resolve(config.calibre.work_dir) / "mpw" / flow_name
