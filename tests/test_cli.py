from pathlib import Path

from typer.testing import CliRunner

from autompw.cli import app


def test_init_writes_default_config(tmp_path: Path):
    runner = CliRunner()
    path = tmp_path / "custom.yaml"
    result = runner.invoke(app, ["init", str(path)])

    assert result.exit_code == 0
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "mpw:" in text
    assert "dicing_margin_um" not in text
    assert "replace_with_placeholder" in text


def test_init_defaults_to_mpw_config_yaml(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (tmp_path / "mpw_config.yaml").exists()


def test_init_refuses_to_overwrite(tmp_path: Path):
    runner = CliRunner()
    path = tmp_path / "config.yaml"
    path.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(app, ["init", str(path)])

    assert result.exit_code == 1
    assert path.read_text(encoding="utf-8") == "existing\n"
