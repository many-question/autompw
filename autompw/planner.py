from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from .config import DesignConfig, ProjectConfig, load_config

PLAN_REPORT_NAME = "placement_plan.yaml"


@dataclass(frozen=True)
class _Leaf:
    design_index: int
    rotation: int


@dataclass(frozen=True)
class _Cut:
    orientation: str
    first: object
    second: object
    first_size: tuple[int, int]
    second_size: tuple[int, int]


def plan_report_path(config: ProjectConfig) -> Path:
    return config.resolve(config.output.output_dir) / PLAN_REPORT_NAME


def generate_plan_report(config: ProjectConfig, output_path: Path | None = None, allow_rotation: bool = False) -> Path:
    report = build_plan_report(config, allow_rotation=allow_rotation)
    out = output_path or plan_report_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(plan_summary_comment(report) + yaml.safe_dump(report, sort_keys=False), encoding="utf-8")
    return out


def build_plan_report(config: ProjectConfig, allow_rotation: bool = False) -> dict[str, Any]:
    planner = _GuillotinePlanner(config, allow_rotation=allow_rotation)
    plans = planner.solve()
    return {
        "metadata": {
            "config": str(config.config_path),
            "mpw_size_um": [config.mpw.size_um[0], config.mpw.size_um[1]],
            "mpw_origin_um": [config.mpw.origin[0], config.mpw.origin[1]],
            "spacing_um": config.spacing_design_to_design_um,
            "requires_each_configured_design": True,
            "allow_rotation": allow_rotation,
            "rotation_degrees_clockwise": planner.rotations,
            "placement_strategy": "guillotine_min_spacing_then_expand_to_mpw_edges",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "plan_count": len(plans),
        },
        "designs": [_design_report_entry(design) for design in config.designs],
        "plans": plans,
    }


def apply_plan(config_path: Path, plan_number: int, report_path: Path | None = None) -> tuple[Path, Path]:
    config = load_config(config_path)
    report = _load_or_generate_report(config, report_path)
    plans = report.get("plans") or []
    if plan_number < 1 or plan_number > len(plans):
        raise ValueError(f"Plan {plan_number} is out of range; report contains {len(plans)} plan(s)")
    selected = plans[plan_number - 1]

    config_data = yaml.safe_load(config.config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(config_data, dict):
        raise ValueError("Config root must be a mapping")
    source_designs = {str(design["name"]): design for design in config_data.get("designs") or []}
    new_designs = []
    name_counts: dict[str, int] = defaultdict(int)
    for placement in selected.get("placements") or []:
        source_name = str(placement["source_design"])
        if source_name not in source_designs:
            raise ValueError(f"Plan references design {source_name!r}, but current config does not contain it")
        name_counts[source_name] += 1
        new_design = dict(source_designs[source_name])
        new_design["name"] = _instance_name(source_name, name_counts[source_name])
        new_design["coord"] = [float(placement["x_um"]), float(placement["y_um"])]
        new_design["anchor"] = "bottom_left"
        new_design["rotation"] = int(placement["rotation"])
        new_designs.append(new_design)

    config_data["designs"] = new_designs
    backup = _backup_config(config.config_path)
    config.config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
    return config.config_path, backup


def plan_summary_lines(report: dict[str, Any]) -> list[str]:
    plans = list(report.get("plans") or [])
    designs = list(report.get("designs") or [])
    names = [str(design["name"]) for design in designs if isinstance(design, dict) and "name" in design]
    if not plans:
        return ["Total plans: 0", "No feasible plans found."]

    utilizations = [float(plan["utilization_percent"]) for plan in plans]
    instance_counts = [int(plan["instance_count"]) for plan in plans]
    lines = [
        f"Total plans: {len(plans)}",
        f"Utilization range: {min(utilizations):.2f}% - {max(utilizations):.2f}%",
        f"Instance count range: {min(instance_counts)} - {max(instance_counts)}",
        "",
    ]

    headers = ["id", "util", "total", *names]
    rows = []
    for plan in plans:
        counts = plan.get("counts") or {}
        rows.append(
            [
                str(plan["id"]),
                f"{float(plan['utilization_percent']):.2f}%",
                str(plan["instance_count"]),
                *[str(counts.get(name, 0)) for name in names],
            ]
        )
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    lines.append(_format_plan_row(headers, widths))
    lines.append(_format_plan_row(["-" * width for width in widths], widths))
    for row in rows:
        lines.append(_format_plan_row(row, widths))
    return lines


def plan_summary_comment(report: dict[str, Any]) -> str:
    lines = ["# Placement plan summary", *[f"# {line}" if line else "#" for line in plan_summary_lines(report)], ""]
    return "\n".join(lines) + "\n"


def _load_or_generate_report(config: ProjectConfig, report_path: Path | None) -> dict[str, Any]:
    path = report_path or plan_report_path(config)
    if not path.exists():
        generate_plan_report(config, path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Plan report must be a mapping: {path}")
    return data


def _format_plan_row(values: list[str], widths: list[int]) -> str:
    return "  ".join(value.ljust(width) for value, width in zip(values, widths))


def _backup_config(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.bak_useplan_{timestamp}")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def _instance_name(source_name: str, index: int) -> str:
    return source_name if index == 1 else f"{source_name}_{index}"


def _design_report_entry(design: DesignConfig) -> dict[str, Any]:
    return {
        "name": design.name,
        "gds": str(design.gds),
        "topcell": design.topcell,
        "size_um": [design.size_um[0], design.size_um[1]],
        "bottom_left_um": [design.bottom_left[0], design.bottom_left[1]],
    }


class _GuillotinePlanner:
    def __init__(self, config: ProjectConfig, allow_rotation: bool = False) -> None:
        self.config = config
        self.rotations = [0, 90] if allow_rotation else [0]
        self.unit_um = config.gds.dbu_um
        self.width = self._to_units(config.mpw.size_um[0])
        self.height = self._to_units(config.mpw.size_um[1])
        self.gap = self._to_units(config.spacing_design_to_design_um)
        self.designs = config.designs
        self.sizes = [self._size_units(design.size_um) for design in self.designs]
        self.areas_um2 = [design.size_um[0] * design.size_um[1] for design in self.designs]
        self.container_area_um2 = config.mpw.size_um[0] * config.mpw.size_um[1]

    def solve(self) -> list[dict[str, Any]]:
        counts = self._candidate_counts()
        dp: dict[tuple[int, ...], dict[tuple[int, int], object]] = {}
        for index, (width, height) in enumerate(self.sizes):
            state = tuple(1 if i == index else 0 for i in range(len(self.designs)))
            boxes: dict[tuple[int, int], object] = {}
            for rotation in self.rotations:
                box = (height, width) if rotation in {90, 270} else (width, height)
                if box[0] <= self.width and box[1] <= self.height:
                    boxes.setdefault(box, _Leaf(index, rotation))
            if boxes:
                dp[state] = _prune(boxes)

        by_total: dict[int, list[tuple[int, ...]]] = defaultdict(list)
        for count in counts:
            by_total[sum(count)].append(count)

        for total in sorted(by_total):
            if total == 1:
                continue
            for count in by_total[total]:
                boxes: dict[tuple[int, int], object] = {}
                for first_count in product(*[range(value + 1) for value in count]):
                    if sum(first_count) == 0 or first_count == count:
                        continue
                    second_count = tuple(count[i] - first_count[i] for i in range(len(count)))
                    if first_count > second_count:
                        continue
                    first_boxes = dp.get(first_count)
                    second_boxes = dp.get(second_count)
                    if not first_boxes or not second_boxes:
                        continue
                    self._combine_boxes(boxes, first_boxes, second_boxes)
                if boxes:
                    dp[count] = _prune(boxes)

        plans = []
        for count, boxes in dp.items():
            if not boxes or any(value < 1 for value in count):
                continue
            bbox, tree = min(boxes.items(), key=lambda item: (item[0][0] * item[0][1], max(item[0])))
            plans.append(self._report_plan(len(plans) + 1, count, bbox, tree))
        plans.sort(
            key=lambda plan: (-plan["utilization_percent"], -plan["instance_count"], plan["compact_bbox_area_um2"])
        )
        for index, plan in enumerate(plans, start=1):
            plan["id"] = index
        return plans

    def _candidate_counts(self) -> list[tuple[int, ...]]:
        max_counts = [int(self.container_area_um2 // area) for area in self.areas_um2]
        counts = []
        for count in product(*[range(value + 1) for value in max_counts]):
            if sum(count) == 0:
                continue
            area = sum(count[i] * self.areas_um2[i] for i in range(len(count)))
            if area <= self.container_area_um2:
                counts.append(tuple(int(value) for value in count))
        return sorted(counts, key=sum)

    def _combine_boxes(
        self,
        out: dict[tuple[int, int], object],
        first_boxes: dict[tuple[int, int], object],
        second_boxes: dict[tuple[int, int], object],
    ) -> None:
        for first_size, first_tree in first_boxes.items():
            for second_size, second_tree in second_boxes.items():
                width = first_size[0] + self.gap + second_size[0]
                height = max(first_size[1], second_size[1])
                if width <= self.width and height <= self.height:
                    out.setdefault((width, height), _Cut("vertical", first_tree, second_tree, first_size, second_size))
                width = max(first_size[0], second_size[0])
                height = first_size[1] + self.gap + second_size[1]
                if width <= self.width and height <= self.height:
                    out.setdefault((width, height), _Cut("horizontal", first_tree, second_tree, first_size, second_size))

    def _report_plan(
        self,
        plan_id: int,
        count: tuple[int, ...],
        bbox: tuple[int, int],
        tree: object,
    ) -> dict[str, Any]:
        placements: list[dict[str, Any]] = []
        cut_tree = self._expanded_tree_report(tree, 0, 0, self.width, self.height, placements)
        compact_bbox_um = [self._to_um(bbox[0]), self._to_um(bbox[1])]
        bbox_um = [self.config.mpw.size_um[0], self.config.mpw.size_um[1]]
        used_area = sum(count[i] * self.areas_um2[i] for i in range(len(count)))
        placements.sort(key=lambda item: (item["x_um"], item["y_um"], item["source_design"], item["rotation"]))
        for index, placement in enumerate(placements, start=1):
            placement["instance"] = index
        return {
            "id": plan_id,
            "utilization_percent": round(used_area / self.container_area_um2 * 100, 6),
            "used_area_um2": round(used_area, 6),
            "instance_count": sum(count),
            "compact_bbox_um": compact_bbox_um,
            "compact_bbox_area_um2": round(compact_bbox_um[0] * compact_bbox_um[1], 6),
            "bbox_um": bbox_um,
            "bbox_area_um2": round(bbox_um[0] * bbox_um[1], 6),
            "counts": {self.designs[i].name: count[i] for i in range(len(count)) if count[i]},
            "placements": placements,
            "cut_tree": cut_tree,
        }

    def _expanded_tree_report(
        self,
        tree: object,
        x: int,
        y: int,
        width: int,
        height: int,
        placements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        region = self._region_um(x, y, width, height)
        if isinstance(tree, _Leaf):
            design = self.designs[tree.design_index]
            chip_width, chip_height = self._tree_size(tree)
            chip_x = self._align_leaf_axis(x, width, chip_width, self.width)
            chip_y = self._align_leaf_axis(y, height, chip_height, self.height)
            placement = {
                "source_design": design.name,
                "rotation": tree.rotation,
                "x_um": self._to_um(chip_x) + self.config.mpw.origin[0],
                "y_um": self._to_um(chip_y) + self.config.mpw.origin[1],
                "width_um": self._to_um(chip_width),
                "height_um": self._to_um(chip_height),
            }
            placements.append(placement)
            return {
                "type": "chip",
                "source_design": design.name,
                "rotation": tree.rotation,
                "region_um": region,
                "chip_region_um": self._region_um(chip_x, chip_y, chip_width, chip_height),
            }
        assert isinstance(tree, _Cut)
        if tree.orientation == "vertical":
            gap = width - tree.first_size[0] - tree.second_size[0]
            first = self._expanded_tree_report(tree.first, x, y, tree.first_size[0], height, placements)
            second = self._expanded_tree_report(
                tree.second,
                x + tree.first_size[0] + gap,
                y,
                tree.second_size[0],
                height,
                placements,
            )
            return {
                "type": "vertical_cut",
                "region_um": region,
                "cut_x_um": self._to_um(x + tree.first_size[0]) + self.config.mpw.origin[0],
                "gap_um": self._to_um(gap),
                "left": first,
                "right": second,
            }
        gap = height - tree.first_size[1] - tree.second_size[1]
        first = self._expanded_tree_report(tree.first, x, y, width, tree.first_size[1], placements)
        second = self._expanded_tree_report(
            tree.second,
            x,
            y + tree.first_size[1] + gap,
            width,
            tree.second_size[1],
            placements,
        )
        return {
            "type": "horizontal_cut",
            "region_um": region,
            "cut_y_um": self._to_um(y + tree.first_size[1]) + self.config.mpw.origin[1],
            "gap_um": self._to_um(gap),
            "bottom": first,
            "top": second,
        }

    def _region_um(self, x: int, y: int, width: int, height: int) -> list[float]:
        return [
            self._to_um(x) + self.config.mpw.origin[0],
            self._to_um(y) + self.config.mpw.origin[1],
            self._to_um(width),
            self._to_um(height),
        ]

    def _align_leaf_axis(self, start: int, region_size: int, chip_size: int, full_size: int) -> int:
        if region_size <= chip_size:
            return start
        touches_min = start == 0
        touches_max = start + region_size == full_size
        if touches_min and not touches_max:
            return start
        if touches_max and not touches_min:
            return start + region_size - chip_size
        return start + (region_size - chip_size) // 2

    def _tree_size(self, tree: object) -> tuple[int, int]:
        if isinstance(tree, _Leaf):
            width, height = self.sizes[tree.design_index]
            return (height, width) if tree.rotation in {90, 270} else (width, height)
        assert isinstance(tree, _Cut)
        if tree.orientation == "vertical":
            return tree.first_size[0] + self.gap + tree.second_size[0], max(tree.first_size[1], tree.second_size[1])
        return max(tree.first_size[0], tree.second_size[0]), tree.first_size[1] + self.gap + tree.second_size[1]

    def _size_units(self, size_um: tuple[float, float]) -> tuple[int, int]:
        return self._to_units(size_um[0]), self._to_units(size_um[1])

    def _to_units(self, value_um: float) -> int:
        return int(round(value_um / self.unit_um))

    def _to_um(self, value_units: int) -> float:
        value = value_units * self.unit_um
        return round(value, 6)


def _prune(boxes: dict[tuple[int, int], object]) -> dict[tuple[int, int], object]:
    kept = {}
    best_height = None
    for (width, height), tree in sorted(boxes.items(), key=lambda item: (item[0][0], item[0][1])):
        if best_height is None or height < best_height:
            kept[(width, height)] = tree
            best_height = height
    return kept
