from pathlib import Path

import klayout.db as kdb
import yaml
from typer.testing import CliRunner

from autompw.cli import app
from autompw.gds_io import write_gds_inspection_text


def test_init_writes_default_config(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init", "tsmc28"])
        path = Path("mpw_config.yaml")

        assert result.exit_code == 0
        assert path.exists()
        assert Path("deck/dmfill_metal").exists()
        assert Path("deck/dmfill_odpo").exists()
        assert Path("input").is_dir()
        assert Path("output").is_dir()
        assert Path("work").is_dir()
        text = path.read_text(encoding="utf-8")
        assert "mpw:" in text
        assert "dicing_margin_um" not in text
        assert "replace_with_placeholder" in text


def test_init_supports_tsmc180_template(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init", "tsmc180"])

        assert result.exit_code == 0
        assert Path("mpw_config.yaml").exists()
        assert Path("deck/dmfill_metal").exists()
        assert Path("deck/dmfill_odpo").exists()
        text = Path("mpw_config.yaml").read_text(encoding="utf-8")
        assert "location: inside" in text
        assert "include_mpw: true" in text
        assert "layer: [150, 15]" in text
        assert "deck_template: ./deck/dmfill_odpo" in text


def test_init_requires_process_name():
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code != 0


def test_init_refuses_to_overwrite(tmp_path: Path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        path = Path("mpw_config.yaml")
        path.write_text("existing\n", encoding="utf-8")
        result = runner.invoke(app, ["init", "tsmc28"])

        assert result.exit_code == 1
        assert path.read_text(encoding="utf-8") == "existing\n"


def test_version_outputs_package_location():
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert "autompw 0.2.3" in result.output
    assert "module " in result.output


def test_check_outputs_each_category_as_it_runs(tmp_path: Path):
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
    size_um: [10, 10]
    coord: [0, 0]
    anchor: bottom_left
    replace_with_placeholder: true
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["check", str(config), "--no-probe-calibre"])

    assert result.exit_code == 0
    assert "[geometry] - CHECKING..." in result.output
    assert "[geometry] - OK:" in result.output
    assert "[design_gds] - CHECKING..." in result.output
    assert "[design_gds] - WARNING:" in result.output
    assert "[calibre_command] - CHECKING..." in result.output
    assert "[calibre_command] - WARNING:" in result.output


def test_inspect_gds_writes_plain_text_report(tmp_path: Path):
    gds = tmp_path / "sample.gds"
    _write_sample_gds(gds)

    result = CliRunner().invoke(app, ["inspect-gds", str(gds)])

    report = tmp_path / "sample.txt"
    assert result.exit_code == 0
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "topcells:" in text
    assert "TOP" in text
    assert "size_um: 10.000000, 20.000000" in text
    assert "1/0" in text
    assert "text report:" in result.output


def test_inspect_gds_reports_sram_capacity(tmp_path: Path):
    gds = tmp_path / "sram.gds"
    _write_sram_gds(gds)

    report = write_gds_inspection_text(gds, sram_prefixes=("TS1N28HPCPLVTB",))

    text = report.read_text(encoding="utf-8")
    assert "sram:" in text
    assert "total_bits: 245760" in text
    assert "TOP/WRAP/TS1N28HPCPLVTB512X80M4S" in text
    assert "512x80" in text
    assert "bits=40960" in text
    assert "count=6" in text


def test_plan_outputs_readable_summary_and_allow_rotation_option(tmp_path: Path):
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
  - name: wide
    gds: ./wide.gds
    size_um: [60, 40]
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

    result = CliRunner().invoke(app, ["plan", str(config), "--allow-rotation"])

    assert result.exit_code == 0
    assert "Total plans:" in result.output
    assert "Utilization range:" in result.output
    assert "Instance count range:" in result.output
    assert "id" in result.output
    assert "util" in result.output
    assert "total" in result.output
    assert "wide" in result.output
    assert "small" in result.output
    report = yaml.safe_load((tmp_path / "output" / "placement_plan.yaml").read_text(encoding="utf-8"))
    assert report["metadata"]["allow_rotation"] is True


def test_preview_outputs_files_and_console_summary(tmp_path: Path):
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
  - name: left
    gds: ./left.gds
    size_um: [40, 100]
    coord: [0, 0]
    anchor: bottom_left
  - name: right
    gds: ./right.gds
    size_um: [40, 100]
    coord: [60, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["preview", str(config)])

    assert result.exit_code == 0
    assert "preview svg:" in result.output
    assert "preview html:" in result.output
    assert "preview png:" in result.output
    assert "utilization: 80.00%" in result.output
    assert "guillotine cuts: 1" in result.output
    assert "issues: none" in result.output
    assert (tmp_path / "output" / "placement_preview.svg").exists()
    assert (tmp_path / "output" / "placement_preview.html").exists()
    assert (tmp_path / "output" / "placement_preview.png").exists()


def _write_sample_gds(path: Path) -> None:
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("TOP")
    top.shapes(layout.layer(1, 0)).insert(kdb.Box(0, 0, 10000, 20000))
    layout.write(str(path))


def _write_sram_gds(path: Path) -> None:
    layout = kdb.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("TOP")
    wrapper = layout.create_cell("WRAP")
    sram = layout.create_cell("TS1N28HPCPLVTB512X80M4S")
    wrapper.insert(
        kdb.CellInstArray(
            sram.cell_index(),
            kdb.Trans(),
            kdb.Vector(1000, 0),
            kdb.Vector(0, 1000),
            2,
            3,
        )
    )
    top.insert(kdb.CellInstArray(wrapper.cell_index(), kdb.Trans()))
    layout.write(str(path))
