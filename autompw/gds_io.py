from __future__ import annotations

from pathlib import Path

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
