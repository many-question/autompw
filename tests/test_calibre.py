from pathlib import Path

from autompw.calibre import render_deck
from autompw.config import load_config
from autompw.dummy import build_mpw_dummy_tasks, build_placeholder_tasks
from autompw.report import check_calibre_decks
from autompw.templates import init_process


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


def test_render_deck_strips_utf8_bom(tmp_path: Path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "metal.tpl").write_bytes(
        b'\xef\xbb\xbfLAYOUT PATH "old.gds"\n'
        b'LAYOUT PRIMARY "OLD"\n'
        b'DRC RESULTS DATABASE "old_out.gds" GDSII _DM\n'
        b'DRC SUMMARY REPORT "old.sum"\n'
        b'VARIABLE xLB   1\n'
        b'VARIABLE yLB   2\n'
        b'VARIABLE xRT   3\n'
        b'VARIABLE yRT   4\n'
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

    rendered = render_deck(project, task)

    assert not rendered.read_bytes().startswith(b"\xef\xbb\xbf")


def test_placeholder_task_uses_placeholder_topcell(tmp_path: Path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "metal.tpl").write_text('LAYOUT PRIMARY "OLD"\n', encoding="utf-8")
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
    size_um: [10, 12]
    coord: [0, 0]
    anchor: bottom_left
    replace_with_placeholder: true
""",
        encoding="utf-8",
    )
    project = load_config(config)
    task = build_placeholder_tasks(project, project.designs[0])[0]
    assert task.input_topcell == "PLACEHOLDER_a"
    assert task.width_um == 10
    assert task.height_um == 12
    assert task.x0_um == 0
    assert task.y0_um == 0


def test_placeholder_task_uses_local_window_even_when_design_coord_is_offset(tmp_path: Path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "metal.tpl").write_text('LAYOUT PRIMARY "OLD"\n', encoding="utf-8")
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
    size_um: [10, 12]
    coord: [25, 30]
    anchor: bottom_left
    replace_with_placeholder: true
""",
        encoding="utf-8",
    )
    project = load_config(config)
    task = build_placeholder_tasks(project, project.designs[0])[0]
    assert task.x0_um == 0
    assert task.y0_um == 0
    assert task.x1_um == 10
    assert task.y1_um == 12


def test_tsmc180_decks_render_runtime_fields(tmp_path: Path):
    init_process("tsmc180", tmp_path)
    project = load_config(tmp_path / "mpw_config.yaml")

    assert check_calibre_decks(project) == []
    tasks = build_mpw_dummy_tasks(project)
    assert {task.flow_name for task in tasks} == {"metal", "odpo"}

    for task in tasks:
        rendered_path = render_deck(project, task)
        assert not rendered_path.read_bytes().startswith(b"\xef\xbb\xbf")
        rendered = rendered_path.read_text(encoding="utf-8")
        assert "{{" not in rendered
        assert "5V.gds" not in rendered
        assert 'LAYOUT PRIMARY "MPW"' in rendered
        assert "VARIABLE xLB   0" in rendered
        assert "VARIABLE yLB   0" in rendered
        assert "VARIABLE xRT   5000" in rendered
        assert "VARIABLE yRT   5000" in rendered
