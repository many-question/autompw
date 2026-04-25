from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isclose


class Anchor(str, Enum):
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"


@dataclass(frozen=True)
class BBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin

    def as_list(self) -> list[float]:
        return [self.xmin, self.ymin, self.xmax, self.ymax]

    def contains(self, other: "BBox", tol: float = 1e-9) -> bool:
        return (
            other.xmin >= self.xmin - tol
            and other.ymin >= self.ymin - tol
            and other.xmax <= self.xmax + tol
            and other.ymax <= self.ymax + tol
        )

    def overlaps(self, other: "BBox", tol: float = 1e-9) -> bool:
        return not (
            self.xmax <= other.xmin + tol
            or other.xmax <= self.xmin + tol
            or self.ymax <= other.ymin + tol
            or other.ymax <= self.ymin + tol
        )

    def spacing_to(self, other: "BBox") -> float:
        if self.overlaps(other, tol=-1e-9):
            return 0.0

        dx = max(other.xmin - self.xmax, self.xmin - other.xmax, 0.0)
        dy = max(other.ymin - self.ymax, self.ymin - other.ymax, 0.0)
        if isclose(dx, 0.0):
            return dy
        if isclose(dy, 0.0):
            return dx
        return (dx * dx + dy * dy) ** 0.5


def bbox_from_anchor(coord: tuple[float, float], size: tuple[float, float], anchor: Anchor) -> BBox:
    x, y = coord
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"Design size must be positive, got {size}")

    x_offsets = {
        Anchor.BOTTOM_LEFT: 0.0,
        Anchor.CENTER_LEFT: 0.0,
        Anchor.TOP_LEFT: 0.0,
        Anchor.BOTTOM_CENTER: -width / 2,
        Anchor.CENTER: -width / 2,
        Anchor.TOP_CENTER: -width / 2,
        Anchor.BOTTOM_RIGHT: -width,
        Anchor.CENTER_RIGHT: -width,
        Anchor.TOP_RIGHT: -width,
    }
    y_offsets = {
        Anchor.BOTTOM_LEFT: 0.0,
        Anchor.BOTTOM_CENTER: 0.0,
        Anchor.BOTTOM_RIGHT: 0.0,
        Anchor.CENTER_LEFT: -height / 2,
        Anchor.CENTER: -height / 2,
        Anchor.CENTER_RIGHT: -height / 2,
        Anchor.TOP_LEFT: -height,
        Anchor.TOP_CENTER: -height,
        Anchor.TOP_RIGHT: -height,
    }
    xmin = x + x_offsets[anchor]
    ymin = y + y_offsets[anchor]
    return BBox(xmin=xmin, ymin=ymin, xmax=xmin + width, ymax=ymin + height)


def require_layer(value: object, field_name: str = "layer") -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field_name} must be [layer, datatype]")
    return int(value[0]), int(value[1])
