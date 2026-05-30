from pathlib import Path

import yaml

from autompw.config import load_config
from autompw.planner import apply_plan, generate_plan_report, plan_report_path


def test_plan_report_lists_guillotine_placements_and_useplan_updates_config(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 100]
  origin: [5, 7]
spacing:
  design_to_design_um: 10
layers:
  marker: [0, 0]
output:
  output_dir: ./output
  framework_gds: framework.gds
  final_gds: final.gds
designs:
  - name: wide
    gds: ./wide.gds
    topcell: WIDE
    size_um: [60, 40]
    coord: [0, 0]
    anchor: bottom_left
  - name: small
    gds: ./small.gds
    topcell: SMALL
    size_um: [30, 30]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)

    report_path = generate_plan_report(project)
    report_text = report_path.read_text(encoding="utf-8")
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))

    assert report_path == plan_report_path(project)
    assert report_text.startswith("# Placement plan summary\n")
    assert "# Total plans:" in report_text
    assert "# plan id" in report_text
    assert report["metadata"]["requires_each_configured_design"] is True
    assert report["metadata"]["mpw_origin_um"] == [5.0, 7.0]
    assert report["metadata"]["allow_rotation"] is False
    assert report["metadata"]["rotation_degrees_clockwise"] == [0]
    assert report["plans"]
    assert report["plans"][0]["id"] == 1
    assert report["plans"][0]["placements"]
    assert "cut_tree" in report["plans"][0]
    assert report["plans"][0]["bbox_um"] == [100.0, 100.0]
    assert report["plans"][0]["compact_bbox_um"][0] <= 100.0
    assert report["plans"][0]["compact_bbox_um"][1] <= 100.0
    assert report["plans"][0]["compact_bbox_area_um2"] <= report["plans"][0]["bbox_area_um2"]
    assert report["plans"][0]["cut_tree"]["region_um"] == [5.0, 7.0, 100.0, 100.0]
    assert _placement_bounds(report["plans"][0]["placements"]) == [5.0, 7.0, 105.0, 107.0]

    updated, backup = apply_plan(config, 1)
    updated_data = yaml.safe_load(updated.read_text(encoding="utf-8"))

    assert backup.exists()
    assert len(updated_data["designs"]) == report["plans"][0]["instance_count"]
    assert all(design["anchor"] == "bottom_left" for design in updated_data["designs"])
    assert all(design["rotation"] == 0 for design in updated_data["designs"])


def test_plan_report_can_allow_rotation(tmp_path: Path):
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
  - name: tall
    gds: ./tall.gds
    size_um: [30, 70]
    coord: [0, 0]
    anchor: bottom_left
  - name: small
    gds: ./small.gds
    size_um: [30, 30]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)

    report_path = generate_plan_report(project, allow_rotation=True)
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))

    assert report["metadata"]["allow_rotation"] is True
    assert report["metadata"]["rotation_degrees_clockwise"] == [0, 90]


def _placement_bounds(placements: list[dict[str, object]]) -> list[float]:
    return [
        min(float(placement["x_um"]) for placement in placements),
        min(float(placement["y_um"]) for placement in placements),
        max(float(placement["x_um"]) + float(placement["width_um"]) for placement in placements),
        max(float(placement["y_um"]) + float(placement["height_um"]) for placement in placements),
    ]
