from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .geometry import Anchor, BBox, bbox_from_anchor, require_layer


@dataclass(frozen=True)
class MPWConfig:
    name: str
    size_um: tuple[float, float]
    origin: tuple[float, float] = (0.0, 0.0)

    @property
    def bbox(self) -> BBox:
        return BBox(
            self.origin[0],
            self.origin[1],
            self.origin[0] + self.size_um[0],
            self.origin[1] + self.size_um[1],
        )


@dataclass(frozen=True)
class DummyBlockerLayer:
    layer: tuple[int, int]
    grow_um: float


@dataclass(frozen=True)
class LayersConfig:
    marker: tuple[int, int]
    dummy_blocker: tuple[DummyBlockerLayer, ...] = ()
    edge_fill_layers: tuple[tuple[int, int], ...] = ()
    edge_fill_width_um: float = 0.45


@dataclass(frozen=True)
class CalibreFlowConfig:
    enabled: bool
    deck_template: Path
    output_suffix: str
    summary_name: str


@dataclass(frozen=True)
class CalibreConfig:
    executable: str = "calibre"
    shell: str | None = None
    setup_script: str | None = None
    args: str = "-drc -hier -turbo 32 -turbo_all -hyper connect"
    work_dir: Path = Path("work")
    flows: dict[str, CalibreFlowConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class GDSConfig:
    topcell: str | None = None
    flatten_final: bool = False
    preserve_child_cells: bool = True
    allow_cell_rename: bool = True
    dbu_um: float = 0.001


@dataclass(frozen=True)
class OutputConfig:
    output_dir: Path
    framework_gds: Path
    final_gds: Path


@dataclass(frozen=True)
class DesignConfig:
    name: str
    gds: Path
    size_um: tuple[float, float]
    coord: tuple[float, float]
    anchor: Anchor
    bottom_left: tuple[float, float] = (0.0, 0.0)
    topcell: str | None = None
    replace_with_placeholder: bool = False

    @property
    def bbox(self) -> BBox:
        return bbox_from_anchor(self.coord, self.size_um, self.anchor)


@dataclass(frozen=True)
class ProjectConfig:
    config_path: Path
    mpw: MPWConfig
    layers: LayersConfig
    calibre: CalibreConfig
    output: OutputConfig
    designs: tuple[DesignConfig, ...]
    spacing_design_to_design_um: float
    gds: GDSConfig

    @property
    def root(self) -> Path:
        return self.config_path.parent

    @property
    def topcell(self) -> str:
        return self.gds.topcell or self.mpw.name

    def resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else (self.root / path)


def load_config(path: str | Path) -> ProjectConfig:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")

    mpw = _parse_mpw(data.get("mpw") or {})
    layers = _parse_layers(data.get("layers") or {})
    calibre = _parse_calibre(data.get("calibre") or {})
    output = _parse_output(data.get("output") or {})
    designs = tuple(_parse_design(d) for d in data.get("designs") or [])
    if not designs:
        raise ValueError("At least one design is required")

    spacing_data = data.get("spacing") or {}
    spacing = float(spacing_data.get("design_to_design_um", 50.0))
    gds = _parse_gds(data.get("gds") or {})

    return ProjectConfig(
        config_path=config_path,
        mpw=mpw,
        layers=layers,
        calibre=calibre,
        output=output,
        designs=designs,
        spacing_design_to_design_um=spacing,
        gds=gds,
    )


def _pair_float(value: Any, field_name: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field_name} must be [x, y]")
    return float(value[0]), float(value[1])


def _parse_mpw(data: dict[str, Any]) -> MPWConfig:
    return MPWConfig(
        name=str(data.get("name") or "MPW_TOP"),
        size_um=_pair_float(data.get("size_um"), "mpw.size_um"),
        origin=_pair_float(data.get("origin", [0, 0]), "mpw.origin"),
    )


def _parse_layers(data: dict[str, Any]) -> LayersConfig:
    dummy = data.get("dummy_blocker") or {}
    blocker_layers = []
    for item in dummy.get("layers") or []:
        if isinstance(item, dict):
            blocker_layers.append(
                DummyBlockerLayer(
                    layer=require_layer(item.get("layer"), "dummy_blocker.layers[].layer"),
                    grow_um=float(item.get("grow_um", 0.0)),
                )
            )
        else:
            blocker_layers.append(DummyBlockerLayer(layer=require_layer(item), grow_um=float(dummy.get("grow_um", 0.0))))

    edge = data.get("edge_fill") or data.get("edge_ring") or {}
    return LayersConfig(
        marker=require_layer(data.get("marker", [0, 0]), "layers.marker"),
        dummy_blocker=tuple(blocker_layers),
        edge_fill_layers=tuple(require_layer(layer, "edge_fill.layers[]") for layer in edge.get("layers") or []),
        edge_fill_width_um=float(edge.get("ring_width_um", edge.get("width_um", 0.45))),
    )


def _parse_calibre(data: dict[str, Any]) -> CalibreConfig:
    flows = {}
    for name, flow in (data.get("flows") or {}).items():
        flows[str(name)] = CalibreFlowConfig(
            enabled=bool(flow.get("enabled", True)),
            deck_template=Path(flow["deck_template"]),
            output_suffix=str(flow.get("output_suffix", f"_{name}")),
            summary_name=str(flow.get("summary_name", f"{name}.sum")),
        )
    return CalibreConfig(
        executable=str(data.get("executable", "calibre")),
        shell=data.get("shell"),
        setup_script=data.get("setup_script"),
        args=str(data.get("args", "-drc -hier -turbo 32 -turbo_all -hyper connect")),
        work_dir=Path(data.get("work_dir", "work")),
        flows=flows,
    )


def _parse_output(data: dict[str, Any]) -> OutputConfig:
    output_dir = Path(data.get("output_dir", data.get("build_dir", "output")))
    return OutputConfig(
        output_dir=output_dir,
        framework_gds=_output_path(output_dir, data.get("framework_gds", "framework.gds")),
        final_gds=_output_path(output_dir, data.get("final_gds", "mpw.gds")),
    )


def _output_path(output_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or path.parent != Path("."):
        return path
    return output_dir / path


def _parse_gds(data: dict[str, Any]) -> GDSConfig:
    return GDSConfig(
        topcell=data.get("topcell"),
        flatten_final=bool(data.get("flatten_final", False)),
        preserve_child_cells=bool(data.get("preserve_child_cells", True)),
        allow_cell_rename=bool(data.get("allow_cell_rename", True)),
        dbu_um=float(data.get("dbu_um", data.get("dbu", 0.001))),
    )


def _parse_design(data: dict[str, Any]) -> DesignConfig:
    return DesignConfig(
        name=str(data["name"]),
        gds=Path(data["gds"]),
        topcell=data.get("topcell"),
        size_um=_pair_float(data["size_um"], "design.size_um"),
        coord=_pair_float(data["coord"], "design.coord"),
        anchor=Anchor(data.get("anchor", "bottom_left")),
        bottom_left=_pair_float(data.get("bottom_left", [0, 0]), "design.bottom_left"),
        replace_with_placeholder=bool(data.get("replace_with_placeholder", False)),
    )
