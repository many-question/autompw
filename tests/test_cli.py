from pathlib import Path

from typer.testing import CliRunner

from autompw.cli import app


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
