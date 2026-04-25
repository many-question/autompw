from pathlib import Path

from autompw.calibre import render_deck
from autompw.config import load_config
from autompw.dummy import build_mpw_dummy_tasks


def test_render_deck_replaces_runtime_header_fields(tmp_path: Path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "metal.tpl").write_text(
        """
LAYOUT PATH "old.gds"
LAYOUT PRIMARY "OLD"
DRC RESULTS DATABASE "old_out.gds" GDSII _DM
DRC SUMMARY REPORT "old.sum"
VARIABLE xLB   1
VARIABLE yLB   2
VARIABLE xRT   3
VARIABLE yRT   4
#DEFINE FILL_DM1
""",
        encoding="utf-8",
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [100, 80]
layers:
  marker: [0, 0]
calibre:
  work_dir: ./build/calibre
  flows:
    metal:
      deck_template: ./templates/metal.tpl
      output_suffix: _DM
      summary_name: DM.sum
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: a
    gds: ./a.gds
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )
    project = load_config(config)
    task = build_mpw_dummy_tasks(project)[0]
    rendered = render_deck(project, task).read_text(encoding="utf-8")
    assert 'LAYOUT PRIMARY "MPW_TEST"' in rendered
    assert "VARIABLE xRT   100" in rendered
    assert "VARIABLE yRT   80" in rendered
    assert "#DEFINE FILL_DM1" in rendered
