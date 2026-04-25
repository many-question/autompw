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
