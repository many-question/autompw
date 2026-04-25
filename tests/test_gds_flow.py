from pathlib import Path

import klayout.db as kdb

from autompw.assemble import assemble
from autompw.config import load_config
from autompw.framework import generate_blank_blocker, generate_framework
from autompw.gds_io import get_top_cell, read_layout


def test_framework_and_assemble_mock_gds(tmp_path: Path):
    input_gds = tmp_path / "block.gds"
    _write_mock_block(input_gds)
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
mpw:
  name: MPW_TEST
  size_um: [100, 100]
layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 0]
        grow_um: 1
  edge_fill:
    layers: [[5, 0]]
    ring_width_um: 0.45
gds:
  topcell: MPW_TEST
  dbu_um: 0.001
output:
  build_dir: ./build
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: block
    gds: {input_gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [20, 20]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)

    framework = generate_framework(project)
    final = assemble(project)

    assert framework.exists()
    assert final.exists()
    framework_layout = read_layout(framework)
    framework_top = get_top_cell(framework_layout, "MPW_TEST")
    marker_layer = framework_layout.layer(0, 0)
    marker_boxes = [shape.box for shape in framework_top.shapes(marker_layer).each() if shape.is_box()]
    assert kdb.Box(0, 0, 100000, 100000) in marker_boxes
    final_layout = read_layout(final)
    top = get_top_cell(final_layout, "MPW_TEST")
    assert top.bbox().width() > 0


def test_blank_blocker_uses_design_size(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
layers:
  marker: [0, 0]
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: block
    gds: ./block.gds
    size_um: [12, 8]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)
    out = tmp_path / "blank.gds"
    generate_blank_blocker(project, project.designs[0], out)
    blank_layout = read_layout(out)
    top = get_top_cell(blank_layout, "DUMMY_block")
    assert top.bbox().width() == 12000
    assert top.bbox().height() == 8000


def test_framework_clips_expanded_layers_to_mpw_bbox(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 0]
        grow_um: 5
  edge_fill:
    layers: [[5, 0]]
    ring_width_um: 2
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: block
    gds: ./block.gds
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)
    framework = generate_framework(project)
    layout = read_layout(framework)
    top = get_top_cell(layout, "MPW_TEST")

    blocker_region = kdb.Region(top.begin_shapes_rec(layout.layer(150, 0)))
    edge_region = kdb.Region(top.begin_shapes_rec(layout.layer(5, 0)))

    assert blocker_region.bbox().left == 0
    assert blocker_region.bbox().bottom == 0
    assert edge_region.bbox().left == 0
    assert edge_region.bbox().bottom == 0


def _write_mock_block(path: Path) -> None:
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("BLOCK")
    layer = layout.layer(31, 0)
    top.shapes(layer).insert(kdb.Box(0, 0, 10000, 10000))
    layout.write(str(path))
