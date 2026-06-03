import struct
from pathlib import Path

from autompw.config import load_config
from autompw.preview import _draw_text, generate_preview


def test_preview_writes_svg_html_png_and_flags_geometry_issues(tmp_path: Path):
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
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: final.gds
designs:
  - name: A
    gds: ./a.gds
    size_um: [30, 30]
    coord: [0, 0]
    anchor: bottom_left
  - name: B
    gds: ./b.gds
    size_um: [30, 30]
    coord: [20, 0]
    anchor: bottom_left
  - name: C
    gds: ./c.gds
    size_um: [10, 10]
    coord: [60, 0]
    anchor: bottom_left
  - name: D
    gds: ./d.gds
    size_um: [10, 10]
    coord: [75, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    result = generate_preview(load_config(config))

    assert result.svg_path.exists()
    assert result.html_path.exists()
    assert result.png_path.exists()
    assert result.png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert result.utilization_percent == 20.0
    issue_kinds = {issue.kind for issue in result.issues}
    assert "overlap" in issue_kinds
    assert "clearance" in issue_kinds
    svg = result.svg_path.read_text(encoding="utf-8")
    html = result.html_path.read_text(encoding="utf-8")
    assert 'class="overlap"' in svg
    assert 'class="clearance"' in svg
    assert "Guillotine Slicing" in html
    assert "Issues" in html


def test_preview_reports_guillotine_cuts_for_sliceable_layout(tmp_path: Path):
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
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: final.gds
designs:
  - name: LEFT
    gds: ./left.gds
    size_um: [40, 100]
    coord: [0, 0]
    anchor: bottom_left
  - name: RIGHT
    gds: ./right.gds
    size_um: [40, 100]
    coord: [60, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    result = generate_preview(load_config(config))

    assert not result.issues
    assert len(result.cuts) == 1
    assert result.cuts[0].orientation == "vertical"
    assert result.cuts[0].bbox.as_list() == [40.0, 0.0, 60.0, 100.0]
    svg = result.svg_path.read_text(encoding="utf-8")
    assert 'class="cut-lane"' in svg
    assert 'class="cut-label"' in svg
    assert ">1</text>" in svg
    png = result.png_path.read_bytes()
    width, height = struct.unpack(">II", png[16:24])
    assert width > height


def test_preview_bitmap_text_draws_pixels():
    pixels = bytearray([255, 255, 255] * 30 * 20)

    _draw_text(pixels, 30, 20, 1, 1, "A1", (0, 0, 0), scale=1)

    assert any(value == 0 for value in pixels)
