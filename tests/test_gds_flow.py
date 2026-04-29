from pathlib import Path

import klayout.db as kdb

from autompw.assemble import assemble
from autompw.config import load_config
from autompw.dummy import merge_placeholder_outputs
from autompw.framework import FRAMEWORK_LABEL_HEIGHT_UM, _design_label_region, generate_blank_placeholder, generate_framework
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
    marker_shapes = list(framework_top.shapes(marker_layer).each())
    assert any(shape.is_polygon() for shape in marker_shapes)
    final_layout = read_layout(final)
    top = get_top_cell(final_layout, "MPW_TEST")
    assert top.bbox().width() > 0


def test_blank_placeholder_uses_design_size_and_marker_only(tmp_path: Path):
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
    generate_blank_placeholder(project, project.designs[0], out)
    blank_layout = read_layout(out)
    top = get_top_cell(blank_layout, "PLACEHOLDER_block")
    assert top.bbox().width() == 12000
    assert top.bbox().height() == 8000
    assert top.begin_shapes_rec(blank_layout.layer(150, 0)).at_end()
    assert top.begin_shapes_rec(blank_layout.layer(5, 0)).at_end()


def test_framework_label_region_has_100um_design_height():
    region = _design_label_region("block", 0.001)
    assert int(round(FRAMEWORK_LABEL_HEIGHT_UM / 0.001)) >= region.bbox().height()
    assert region.bbox().height() > int(round(80 / 0.001))


def test_merge_placeholder_outputs_combines_marker_and_dummy(tmp_path: Path):
    dummy_gds = tmp_path / "dummy_metal.gds"
    _write_mock_block(dummy_gds, topcell="DUMMY", layer=(32, 0))
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
layers:
  marker: [0, 0]
output:
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: mpw.gds
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
    design = project.designs[0]
    marker = tmp_path / "marker.gds"
    generate_blank_placeholder(project, design, marker)

    merged = merge_placeholder_outputs(project, design, marker, [dummy_gds])

    layout = read_layout(merged)
    top = get_top_cell(layout, "PLACEHOLDER_block")
    assert not top.begin_shapes_rec(layout.layer(0, 0)).at_end()
    assert not top.begin_shapes_rec(layout.layer(32, 0)).at_end()


def test_assemble_aligns_design_bottom_left_to_reserved_bbox(tmp_path: Path):
    input_gds = tmp_path / "offset_block.gds"
    _write_mock_block(input_gds, box=kdb.Box(5000, 7000, 15000, 17000))
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
mpw:
  name: MPW_TEST
  size_um: [100, 100]
layers:
  marker: [0, 0]
gds:
  topcell: MPW_TEST
  dbu_um: 0.001
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: block
    gds: {input_gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [20, 30]
    anchor: bottom_left
    bottom_left: [5, 7]
""",
        encoding="utf-8",
    )
    project = load_config(config)

    final = assemble(project)

    final_layout = read_layout(final)
    top = get_top_cell(final_layout, "MPW_TEST")
    region = kdb.Region(top.begin_shapes_rec(final_layout.layer(31, 0)))
    assert region.bbox() == kdb.Box(20000, 30000, 30000, 40000)


def test_assemble_reports_design_progress(tmp_path: Path):
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
gds:
  topcell: MPW_TEST
  dbu_um: 0.001
output:
  final_gds: ./build/final.gds
designs:
  - name: block
    gds: {input_gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [20, 30]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)
    messages = []

    assemble(project, progress=messages.append)

    assert "assembling block ... (1/1)" in messages


def test_assemble_keeps_dummy_fill_absolute_coordinates(tmp_path: Path):
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
calibre:
  flows:
    metal:
      deck_template: ./deck.svrf
      output_suffix: _DM
      summary_name: DM.sum
gds:
  topcell: MPW_TEST
  dbu_um: 0.001
output:
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: final.gds
designs:
  - name: block
    gds: {input_gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)
    dummy = tmp_path / "output" / "dummy" / "dummy_metal.gds"
    dummy.parent.mkdir(parents=True)
    _write_mock_block(dummy, box=kdb.Box(20000, 30000, 25000, 35000), topcell="DUMMY", layer=(40, 0))

    final = assemble(project)

    final_layout = read_layout(final)
    top = get_top_cell(final_layout, "MPW_TEST")
    region = kdb.Region(top.begin_shapes_rec(final_layout.layer(40, 0)))
    assert region.bbox() == kdb.Box(20000, 30000, 25000, 35000)


def test_assemble_places_placeholder_origin_at_reserved_bbox(tmp_path: Path):
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
gds:
  topcell: MPW_TEST
  dbu_um: 0.001
output:
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: final.gds
designs:
  - name: block
    gds: {input_gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [20, 30]
    anchor: bottom_left
    replace_with_placeholder: true
""",
        encoding="utf-8",
    )
    project = load_config(config)
    placeholder = tmp_path / "output" / "placeholders" / "block_placeholder.gds"
    placeholder.parent.mkdir(parents=True)
    _write_mock_block(placeholder, box=kdb.Box(2000, 3000, 7000, 8000), topcell="PLACEHOLDER_block", layer=(41, 0))

    final = assemble(project)

    final_layout = read_layout(final)
    top = get_top_cell(final_layout, "MPW_TEST")
    region = kdb.Region(top.begin_shapes_rec(final_layout.layer(41, 0)))
    assert region.bbox() == kdb.Box(22000, 33000, 27000, 38000)


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


def _write_mock_block(
    path: Path,
    box: kdb.Box | None = None,
    topcell: str = "BLOCK",
    layer: tuple[int, int] = (31, 0),
) -> None:
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell(topcell)
    layer_index = layout.layer(*layer)
    top.shapes(layer_index).insert(box or kdb.Box(0, 0, 10000, 10000))
    layout.write(str(path))
