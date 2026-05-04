from __future__ import annotations

from pathlib import Path
import re
from collections.abc import Sequence

import klayout.db as kdb

from .geometry import BBox


def dbu_to_iu(value_um: float, dbu_um: float) -> int:
    return int(round(value_um / dbu_um))


def iu_to_um(value_iu: int, dbu_um: float) -> float:
    return value_iu * dbu_um


def box_from_bbox(bbox: BBox, dbu_um: float) -> kdb.Box:
    return kdb.Box(
        dbu_to_iu(bbox.xmin, dbu_um),
        dbu_to_iu(bbox.ymin, dbu_um),
        dbu_to_iu(bbox.xmax, dbu_um),
        dbu_to_iu(bbox.ymax, dbu_um),
    )


def bbox_from_box(box: kdb.Box, dbu_um: float) -> BBox:
    return BBox(
        iu_to_um(box.left, dbu_um),
        iu_to_um(box.bottom, dbu_um),
        iu_to_um(box.right, dbu_um),
        iu_to_um(box.top, dbu_um),
    )


def make_layout(dbu_um: float) -> kdb.Layout:
    layout = kdb.Layout()
    layout.dbu = dbu_um
    return layout


def layer_index(layout: kdb.Layout, layer: tuple[int, int]) -> int:
    return layout.layer(int(layer[0]), int(layer[1]))


def write_layout(layout: kdb.Layout, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    layout.write(str(path))


def read_layout(path: Path) -> kdb.Layout:
    layout = kdb.Layout()
    layout.read(str(path))
    return layout


def get_top_cell(layout: kdb.Layout, topcell: str | None = None) -> kdb.Cell:
    if topcell:
        cell = layout.cell(topcell)
        if cell is None:
            raise ValueError(f"Topcell {topcell!r} not found")
        return cell
    tops = list(layout.top_cells())
    if len(tops) != 1:
        names = [cell.name for cell in tops]
        raise ValueError(f"Expected exactly one topcell, found {names}. Specify topcell explicitly.")
    return tops[0]


def inspect_gds(path: Path) -> dict[str, object]:
    layout = read_layout(path)
    tops = list(layout.top_cells())
    layers = sorted((info.layer, info.datatype) for info in layout.layer_infos())
    top_data = []
    for cell in tops:
        top_data.append(
            {
                "name": cell.name,
                "bbox_um": bbox_from_box(cell.bbox(), layout.dbu).as_list() if not cell.bbox().empty() else None,
            }
        )
    return {"path": str(path), "dbu_um": layout.dbu, "topcells": top_data, "layers": layers}


def inspect_sram_instances(path: Path, prefixes: Sequence[str]) -> dict[str, object]:
    layout = read_layout(path)
    patterns = [
        re.compile(rf"^{re.escape(prefix)}(?P<rows>\d+)x(?P<cols>\d+)")
        for prefix in prefixes
        if prefix
    ]
    instances: list[dict[str, object]] = []

    def match_sram(cell_name: str) -> tuple[int, int] | None:
        for pattern in patterns:
            match = pattern.search(cell_name)
            if match:
                return int(match.group("rows")), int(match.group("cols"))
        return None

    def append_sram(cell_path: str, cell_name: str, multiplicity: int) -> None:
        size = match_sram(cell_name)
        if not size:
            return
        rows, cols = size
        bits = rows * cols
        instances.append(
            {
                "path": cell_path,
                "cell": cell_name,
                "rows": rows,
                "cols": cols,
                "bits": bits,
                "multiplicity": multiplicity,
                "total_bits": bits * multiplicity,
            }
        )

    def walk(cell: kdb.Cell, cell_path: str, parent_multiplicity: int) -> None:
        for inst in cell.each_inst():
            child = layout.cell(inst.cell_index)
            if child is None:
                continue
            multiplicity = parent_multiplicity * _instance_multiplicity(inst)
            child_path = f"{cell_path}/{child.name}"
            append_sram(child_path, child.name, multiplicity)
            walk(child, child_path, multiplicity)

    for top in layout.top_cells():
        append_sram(top.name, top.name, 1)
        walk(top, top.name, 1)

    return {
        "prefixes": tuple(prefixes),
        "instances": instances,
        "total_bits": sum(int(instance["total_bits"]) for instance in instances),
    }


def _instance_multiplicity(inst: kdb.Instance) -> int:
    if inst.is_regular_array():
        return max(1, int(inst.na)) * max(1, int(inst.nb))
    return 1


def write_gds_inspection_text(
    path: Path,
    output_path: Path | None = None,
    sram_prefixes: Sequence[str] = (),
) -> Path:
    info = inspect_gds(path)
    sram = inspect_sram_instances(path, sram_prefixes) if sram_prefixes else None
    out = output_path or path.with_suffix(".txt")
    lines = [
        f"path: {info['path']}",
        f"dbu_um: {info['dbu_um']}",
        "topcells:",
    ]
    for topcell in info["topcells"]:
        bbox = topcell["bbox_um"]
        lines.append(f"  {topcell['name']}")
        if bbox is None:
            lines.append("    bbox_um: empty")
            lines.append("    size_um: empty")
        else:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            lines.append(f"    bbox_um: {bbox[0]:.6f}, {bbox[1]:.6f}, {bbox[2]:.6f}, {bbox[3]:.6f}")
            lines.append(f"    size_um: {width:.6f}, {height:.6f}")
    lines.append("layers:")
    for layer, datatype in info["layers"]:
        lines.append(f"{layer}/{datatype}")
    if sram:
        lines.extend(
            [
                "sram:",
                f"prefixes: {', '.join(sram['prefixes'])}",
                f"total_bits: {sram['total_bits']}",
                "instances:",
            ]
        )
        for instance in sram["instances"]:
            lines.append(
                "{path} | {rows}x{cols} | bits={bits} | count={multiplicity} | total_bits={total_bits}".format(
                    **instance
                )
            )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
