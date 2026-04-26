from pathlib import Path

from autompw.config import load_config
import klayout.db as kdb

from autompw.report import check_calibre_decks, check_design_gds, check_geometry


def test_boundary_allows_touching_mpw_edge(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
spacing:
  design_to_design_um: 10
layers:
  marker: [0, 0]
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: edge_block
    gds: ./edge.gds
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    assert check_geometry(load_config(config)) == []


def test_spacing_between_designs_is_checked(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
spacing:
  design_to_design_um: 10
layers:
  marker: [0, 0]
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: a
    gds: ./a.gds
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
  - name: b
    gds: ./b.gds
    size_um: [10, 10]
    coord: [15, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    issues = check_geometry(load_config(config))
    assert len(issues) == 1
    assert "spacing" in issues[0].message


def test_design_gds_missing_is_error(tmp_path: Path):
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
  - name: missing
    gds: ./missing.gds
    topcell: MISSING
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    issues = check_design_gds(load_config(config))
    assert issues[0].severity == "error"
    assert "does not exist" in issues[0].message


def test_placeholder_design_gds_missing_is_warning(tmp_path: Path):
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
  - name: missing
    gds: ./missing.gds
    topcell: MISSING
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
    replace_with_placeholder: true
""",
        encoding="utf-8",
    )

    issues = check_design_gds(load_config(config))
    assert issues[0].severity == "warning"
    assert "does not exist" in issues[0].message


def test_design_gds_size_mismatch_is_warning(tmp_path: Path):
    gds = tmp_path / "block.gds"
    _write_box_gds(gds, "BLOCK", kdb.Box(0, 0, 9000, 10000))
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
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
    gds: {gds.as_posix()}
    topcell: BLOCK
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    issues = check_design_gds(load_config(config))
    assert issues[0].severity == "warning"
    assert "size_um" in issues[0].message


def test_calibre_deck_missing_fields_warns(tmp_path: Path):
    deck = tmp_path / "deck.svrf"
    deck.write_text('LAYOUT PATH "x.gds"\n', encoding="utf-8")
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
      deck_template: {deck.as_posix()}
      output_suffix: _DM
      summary_name: DM.sum
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

    issues = check_calibre_decks(load_config(config))
    assert issues[0].severity == "warning"
    assert "automatic rendering" in issues[0].message


def _write_box_gds(path: Path, topcell: str, box: kdb.Box) -> None:
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell(topcell)
    top.shapes(layout.layer(1, 0)).insert(box)
    layout.write(str(path))
