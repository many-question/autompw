from pathlib import Path

from autompw.config import load_config
from autompw.report import check_project


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

    assert check_project(load_config(config)) == []


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

    issues = check_project(load_config(config))
    assert len(issues) == 1
    assert "spacing" in issues[0].message
