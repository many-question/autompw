from pathlib import Path

from autompw.config import load_config


def test_load_config_with_per_layer_dummy_grow(tmp_path: Path):
    config = tmp_path / "config.yaml"
    config.write_text(
        """
mpw:
  name: MPW_TEST
  size_um: [1000, 800]
layers:
  marker: [0, 0]
  dummy_blocker:
    layers:
      - layer: [150, 0]
        grow_um: 1
      - layer: [150, 1]
        grow_um: 3
calibre:
  flows:
    metal:
      deck_template: ./templates/metal.tpl
      output_suffix: _DM
      summary_name: DM.sum
output:
  framework_gds: ./build/framework.gds
  final_gds: ./build/final.gds
designs:
  - name: block_a
    gds: ./block_a.gds
    size_um: [100, 200]
    coord: [0, 0]
    anchor: bottom_left
""",
        encoding="utf-8",
    )

    loaded = load_config(config)
    assert loaded.mpw.name == "MPW_TEST"
    assert loaded.layers.dummy_blocker[0].layer == (150, 0)
    assert loaded.layers.dummy_blocker[1].grow_um == 3
    assert loaded.calibre.flows["metal"].output_suffix == "_DM"
