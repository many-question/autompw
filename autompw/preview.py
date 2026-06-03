from __future__ import annotations

import html
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .config import DesignConfig, ProjectConfig
from .geometry import BBox

PREVIEW_BASENAME = "placement_preview"
CUT_GAP_COLOR = "#d1d5db"
CUT_LANE_COLOR = "#64748b"
CUT_LABEL_COLOR = "#111827"
CUT_LABEL_TEXT_COLOR = "#ffffff"

FONT_5X7 = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00001", "00001", "00001", "00001", "10001", "10001", "01110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "01000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
}


@dataclass(frozen=True)
class PreviewDesign:
    design: DesignConfig
    bbox: BBox
    color: str


@dataclass(frozen=True)
class PreviewIssue:
    severity: str
    kind: str
    message: str
    bbox: BBox | None = None
    line_um: tuple[float, float, float, float] | None = None
    designs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreviewCut:
    orientation: Literal["vertical", "horizontal"]
    bbox: BBox
    depth: int
    left_count: int
    right_count: int


@dataclass(frozen=True)
class PreviewResult:
    svg_path: Path
    html_path: Path
    png_path: Path
    issues: tuple[PreviewIssue, ...]
    cuts: tuple[PreviewCut, ...]
    utilization_percent: float


def generate_preview(
    config: ProjectConfig,
    output_dir: Path | None = None,
    basename: str = PREVIEW_BASENAME,
) -> PreviewResult:
    out_dir = output_dir or config.resolve(config.output.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    designs = _preview_designs(config)
    issues = _placement_issues(config, designs)
    cuts, cut_issue = _guillotine_cuts(config.mpw.bbox, designs, config.spacing_design_to_design_um)
    if cut_issue is not None:
        issues = [*issues, cut_issue]
    utilization = _utilization_percent(config, designs)

    svg = _render_svg(config, designs, issues, cuts, utilization)
    html_text = _render_html(config, svg, designs, issues, cuts, utilization)

    svg_path = out_dir / f"{basename}.svg"
    html_path = out_dir / f"{basename}.html"
    png_path = out_dir / f"{basename}.png"
    svg_path.write_text(svg, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    _write_preview_png(png_path, config, designs, issues, cuts)
    return PreviewResult(svg_path, html_path, png_path, tuple(issues), tuple(cuts), utilization)


def _preview_designs(config: ProjectConfig) -> list[PreviewDesign]:
    palette = [
        "#88c0d0",
        "#a3be8c",
        "#d08770",
        "#b48ead",
        "#ebcb8b",
        "#81a1c1",
        "#e5a3a3",
        "#8fbcbb",
        "#c4a484",
    ]
    return [
        PreviewDesign(design=design, bbox=design.bbox, color=palette[index % len(palette)])
        for index, design in enumerate(config.designs)
    ]


def _utilization_percent(config: ProjectConfig, designs: list[PreviewDesign]) -> float:
    used = sum(item.bbox.width * item.bbox.height for item in designs)
    total = config.mpw.size_um[0] * config.mpw.size_um[1]
    return round(used / total * 100, 6) if total else 0.0


def _utilization_text(config: ProjectConfig, designs: list[PreviewDesign]) -> str:
    return f"{_utilization_percent(config, designs):.2f}%"


def _placement_issues(config: ProjectConfig, designs: list[PreviewDesign]) -> list[PreviewIssue]:
    issues: list[PreviewIssue] = []
    mpw_bbox = config.mpw.bbox
    min_spacing = config.spacing_design_to_design_um

    for item in designs:
        if not mpw_bbox.contains(item.bbox):
            issues.append(
                PreviewIssue(
                    severity="error",
                    kind="outside",
                    message=f"{item.design.name} bbox {_fmt_bbox(item.bbox)} is outside MPW bbox {_fmt_bbox(mpw_bbox)}",
                    bbox=item.bbox,
                    designs=(item.design.name,),
                )
            )

    for index, left in enumerate(designs):
        for right in designs[index + 1 :]:
            if left.bbox.overlaps(right.bbox):
                issues.append(
                    PreviewIssue(
                        severity="error",
                        kind="overlap",
                        message=(
                            f"{left.design.name} bbox {_fmt_bbox(left.bbox)} overlaps "
                            f"{right.design.name} bbox {_fmt_bbox(right.bbox)}"
                        ),
                        bbox=_intersection(left.bbox, right.bbox),
                        designs=(left.design.name, right.design.name),
                    )
                )
                continue
            spacing = left.bbox.spacing_to(right.bbox)
            if spacing < min_spacing:
                marker_bbox, marker_line = _spacing_marker(left.bbox, right.bbox)
                issues.append(
                    PreviewIssue(
                        severity="error",
                        kind="clearance",
                        message=(
                            f"{left.design.name} to {right.design.name} spacing {spacing:.3f}um "
                            f"is below {min_spacing:.3f}um"
                        ),
                        bbox=marker_bbox,
                        line_um=marker_line,
                        designs=(left.design.name, right.design.name),
                    )
                )
    return issues


def _guillotine_cuts(
    region: BBox,
    designs: list[PreviewDesign],
    min_gap: float,
) -> tuple[list[PreviewCut], PreviewIssue | None]:
    success, cuts = _guillotine_cuts_in_region(region, designs, min_gap, 0)
    if success:
        return cuts, None
    return (
        [],
        PreviewIssue(
            severity="warning",
            kind="guillotine",
            message="No full guillotine slicing tree was detected for the current placement",
            bbox=None,
        ),
    )


def _guillotine_cuts_in_region(
    region: BBox,
    designs: list[PreviewDesign],
    min_gap: float,
    depth: int,
) -> tuple[bool, list[PreviewCut]]:
    if len(designs) <= 1:
        return True, []

    candidates = [
        *_cut_candidates(region, designs, min_gap, "vertical"),
        *_cut_candidates(region, designs, min_gap, "horizontal"),
    ]
    candidates.sort(
        key=lambda item: (
            -item["gap"],
            abs(len(item["first"]) - len(item["second"])),
            0 if item["orientation"] == "vertical" else 1,
        )
    )

    for candidate in candidates:
        first_ok, first_cuts = _guillotine_cuts_in_region(candidate["first_region"], candidate["first"], min_gap, depth + 1)
        if not first_ok:
            continue
        second_ok, second_cuts = _guillotine_cuts_in_region(candidate["second_region"], candidate["second"], min_gap, depth + 1)
        if not second_ok:
            continue
        cut = PreviewCut(
            orientation=candidate["orientation"],
            bbox=candidate["cut_bbox"],
            depth=depth,
            left_count=len(candidate["first"]),
            right_count=len(candidate["second"]),
        )
        return True, [cut, *first_cuts, *second_cuts]
    return False, []


def _cut_candidates(
    region: BBox,
    designs: list[PreviewDesign],
    min_gap: float,
    orientation: Literal["vertical", "horizontal"],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    tol = 1e-9
    if orientation == "vertical":
        starts = sorted({region.xmin, *(item.bbox.xmax for item in designs)})
        ends = sorted({region.xmax, *(item.bbox.xmin for item in designs)})
        for start in starts:
            for end in ends:
                gap = end - start
                if gap + tol < min_gap:
                    continue
                first = [item for item in designs if item.bbox.xmax <= start + tol]
                second = [item for item in designs if item.bbox.xmin >= end - tol]
                if not first or not second or len(first) + len(second) != len(designs):
                    continue
                candidates.append(
                    {
                        "orientation": "vertical",
                        "gap": gap,
                        "cut_bbox": BBox(start, region.ymin, end, region.ymax),
                        "first": first,
                        "second": second,
                        "first_region": BBox(region.xmin, region.ymin, start, region.ymax),
                        "second_region": BBox(end, region.ymin, region.xmax, region.ymax),
                    }
                )
    else:
        starts = sorted({region.ymin, *(item.bbox.ymax for item in designs)})
        ends = sorted({region.ymax, *(item.bbox.ymin for item in designs)})
        for start in starts:
            for end in ends:
                gap = end - start
                if gap + tol < min_gap:
                    continue
                first = [item for item in designs if item.bbox.ymax <= start + tol]
                second = [item for item in designs if item.bbox.ymin >= end - tol]
                if not first or not second or len(first) + len(second) != len(designs):
                    continue
                candidates.append(
                    {
                        "orientation": "horizontal",
                        "gap": gap,
                        "cut_bbox": BBox(region.xmin, start, region.xmax, end),
                        "first": first,
                        "second": second,
                        "first_region": BBox(region.xmin, region.ymin, region.xmax, start),
                        "second_region": BBox(region.xmin, end, region.xmax, region.ymax),
                    }
                )
    return candidates


def _render_svg(
    config: ProjectConfig,
    designs: list[PreviewDesign],
    issues: list[PreviewIssue],
    cuts: list[PreviewCut],
    utilization: float,
) -> str:
    mpw = config.mpw.bbox
    plot_max = 850.0
    scale = min(plot_max / mpw.width, plot_max / mpw.height)
    plot_w = mpw.width * scale
    plot_h = mpw.height * scale
    margin = 56.0
    side_w = 370.0
    width = int(math.ceil(plot_w + side_w + margin * 2))
    height = int(math.ceil(max(plot_h + margin * 2, 650)))

    def sx(value: float) -> float:
        return margin + (value - mpw.xmin) * scale

    def sy(value: float) -> float:
        return margin + (mpw.ymax - value) * scale

    def rect_attrs(bbox: BBox) -> str:
        return (
            f'x="{sx(bbox.xmin):.3f}" y="{sy(bbox.ymax):.3f}" '
            f'width="{bbox.width * scale:.3f}" height="{bbox.height * scale:.3f}"'
        )

    issue_designs = _issue_design_map(issues)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Arial,Helvetica,sans-serif;fill:#1f2933}.title{font-size:18px;font-weight:700}.meta{font-size:12px;fill:#4b5563}.chip-label{font-size:12px;font-weight:700}.chip-sub{font-size:10px;fill:#111827}.axis{font-size:10px;fill:#4b5563}.chip{stroke:#1f2937;stroke-width:1.4}.cut-gap{fill:#d1d5db;opacity:.42}.cut-lane{fill:#64748b;opacity:.62}.cut-label-box{fill:#111827;stroke:#ffffff;stroke-width:1.5}.cut-label{font-size:12px;font-weight:700;fill:#ffffff;text-anchor:middle;dominant-baseline:central}.overlap{fill:#ef4444;opacity:.46}.clearance{fill:#f59e0b;opacity:.46}.outside{fill:none;stroke:#ef4444;stroke-width:3;stroke-dasharray:7 5}.warnline{stroke:#f59e0b;stroke-width:3;stroke-dasharray:7 5}",
        "</style>",
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text class="title" x="{margin:.0f}" y="26">AutoMPW Placement Preview</text>',
        (
            f'<text class="meta" x="{margin:.0f}" y="44">'
            f'MPW {mpw.width:.3f} x {mpw.height:.3f} um, {len(designs)} design(s), '
            f'utilization {utilization:.2f}%, spacing rule {config.spacing_design_to_design_um:.3f} um'
            "</text>"
        ),
        f'<rect {rect_attrs(mpw)} fill="#ffffff" stroke="#111827" stroke-width="2"/>',
    ]

    for index, cut in enumerate(cuts, start=1):
        lane = _cut_lane_bbox(cut, config.spacing_design_to_design_um)
        label_x, label_y = _bbox_center(lane)
        lines.append(f'<rect class="cut-gap" {rect_attrs(cut.bbox)}/>')
        lines.append(f'<rect class="cut-lane" {rect_attrs(lane)}/>')
        lines.append(f'<circle class="cut-label-box" cx="{sx(label_x):.3f}" cy="{sy(label_y):.3f}" r="11"/>')
        lines.append(f'<text class="cut-label" x="{sx(label_x):.3f}" y="{sy(label_y):.3f}">{index}</text>')
    for issue in issues:
        if issue.kind == "overlap" and issue.bbox is not None:
            lines.append(f'<rect class="overlap" {rect_attrs(issue.bbox)}/>')
        elif issue.kind == "clearance":
            if issue.bbox is not None:
                lines.append(f'<rect class="clearance" {rect_attrs(issue.bbox)}/>')
            elif issue.line_um is not None:
                x1, y1, x2, y2 = issue.line_um
                lines.append(f'<line class="warnline" x1="{sx(x1):.3f}" y1="{sy(y1):.3f}" x2="{sx(x2):.3f}" y2="{sy(y2):.3f}"/>')

    for item in designs:
        design = item.design
        stroke = "#ef4444" if issue_designs.get(design.name) in {"outside", "overlap"} else "#1f2937"
        stroke_width = "3" if stroke == "#ef4444" else "1.4"
        lines.append(
            f'<rect class="chip" {rect_attrs(item.bbox)} fill="{item.color}" fill-opacity="0.78" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
        )
        if issue_designs.get(design.name) == "outside":
            lines.append(f'<rect class="outside" {rect_attrs(item.bbox)}/>')
        label_x = sx(item.bbox.xmin) + 7
        label_y = sy(item.bbox.ymax) + 18
        lines.append(f'<text class="chip-label" x="{label_x:.3f}" y="{label_y:.3f}">{_esc(design.name)}</text>')
        lines.append(
            f'<text class="chip-sub" x="{label_x:.3f}" y="{label_y + 15:.3f}">'
            f'{item.bbox.width:.0f} x {item.bbox.height:.0f} um, rot {design.rotation}</text>'
        )
        lines.append(
            f'<text class="chip-sub" x="{label_x:.3f}" y="{label_y + 30:.3f}">'
            f'({item.bbox.xmin:.0f}, {item.bbox.ymin:.0f})</text>'
        )

    lines.extend(
        [
            f'<text class="axis" x="{margin:.0f}" y="{margin + plot_h + 18:.0f}">({mpw.xmin:.0f}, {mpw.ymin:.0f})</text>',
            f'<text class="axis" x="{margin + plot_w - 70:.0f}" y="{margin + plot_h + 18:.0f}">({mpw.xmax:.0f}, {mpw.ymin:.0f})</text>',
            f'<text class="axis" x="{margin - 8:.0f}" y="{margin - 10:.0f}">({mpw.xmin:.0f}, {mpw.ymax:.0f})</text>',
        ]
    )

    side_x = margin + plot_w + 28
    side_y = margin + 8
    lines.append(f'<text class="title" x="{side_x:.0f}" y="{side_y:.0f}">Summary</text>')
    side_y += 24
    for text in (
        f"utilization: {utilization:.2f}%",
        f"issues: {len(issues)}",
        f"guillotine cuts: {len(cuts)}" if cuts else "guillotine cuts: not detected",
    ):
        lines.append(f'<text class="meta" x="{side_x:.0f}" y="{side_y:.0f}">{_esc(text)}</text>')
        side_y += 18

    side_y += 10
    lines.append(f'<text class="title" x="{side_x:.0f}" y="{side_y:.0f}">Cuts</text>')
    side_y += 22
    for index, cut in enumerate(cuts[:12], start=1):
        label = (
            f"#{index} {cut.orientation} lane {config.spacing_design_to_design_um:.1f}um, "
            f"gap {cut.bbox.width if cut.orientation == 'vertical' else cut.bbox.height:.1f}um "
            f"({cut.left_count}|{cut.right_count})"
        )
        lines.append(f'<text class="meta" x="{side_x:.0f}" y="{side_y:.0f}">{_esc(label)}</text>')
        side_y += 16
    if not cuts:
        lines.append(f'<text class="meta" x="{side_x:.0f}" y="{side_y:.0f}">No full slicing tree detected.</text>')
        side_y += 16

    side_y += 10
    lines.append(f'<text class="title" x="{side_x:.0f}" y="{side_y:.0f}">Issues</text>')
    side_y += 22
    if issues:
        for issue in issues[:12]:
            lines.append(f'<text class="meta" x="{side_x:.0f}" y="{side_y:.0f}">{_esc(issue.kind)}: {_esc(issue.message[:58])}</text>')
            side_y += 16
    else:
        lines.append(f'<text class="meta" x="{side_x:.0f}" y="{side_y:.0f}">No placement issues found.</text>')

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _render_html(
    config: ProjectConfig,
    svg: str,
    designs: list[PreviewDesign],
    issues: list[PreviewIssue],
    cuts: list[PreviewCut],
    utilization: float,
) -> str:
    issue_rows = "\n".join(
        f"<tr><td>{_esc(issue.severity)}</td><td>{_esc(issue.kind)}</td><td>{_esc(issue.message)}</td></tr>"
        for issue in issues
    ) or '<tr><td colspan="3">No placement issues found.</td></tr>'
    design_rows = "\n".join(
        "<tr>"
        f"<td>{_esc(item.design.name)}</td>"
        f"<td>{_fmt_bbox(item.bbox)}</td>"
        f"<td>{item.design.rotation}</td>"
        f"<td>{_esc(item.design.anchor.value)}</td>"
        f"<td>{'yes' if item.design.replace_with_placeholder else 'no'}</td>"
        "</tr>"
        for item in designs
    )
    cut_rows = "\n".join(
        "<tr>"
        f"<td>{index}</td>"
        f"<td>{_esc(cut.orientation)}</td>"
        f"<td>{_fmt_bbox(cut.bbox)}</td>"
        f"<td>{config.spacing_design_to_design_um:.3f}</td>"
        f"<td>{cut.bbox.width if cut.orientation == 'vertical' else cut.bbox.height:.3f}</td>"
        f"<td>{cut.left_count} | {cut.right_count}</td>"
        "</tr>"
        for index, cut in enumerate(cuts, start=1)
    ) or '<tr><td colspan="6">No full guillotine slicing tree detected.</td></tr>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AutoMPW Placement Preview</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #1f2933; }}
    h1, h2 {{ margin-bottom: 0.35rem; }}
    table {{ border-collapse: collapse; margin: 12px 0 24px; width: 100%; max-width: 1100px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px 8px; text-align: left; font-size: 13px; }}
    th {{ background: #f3f4f6; }}
    .summary {{ margin-bottom: 16px; color: #4b5563; }}
    svg {{ max-width: 100%; height: auto; border: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
  <h1>AutoMPW Placement Preview</h1>
  <div class="summary">
    config: {_esc(str(config.config_path))}<br>
    MPW: {config.mpw.size_um[0]:.3f} x {config.mpw.size_um[1]:.3f} um,
    designs: {len(designs)}, utilization: {utilization:.2f}%,
    spacing rule: {config.spacing_design_to_design_um:.3f} um
  </div>
  {svg}
  <h2>Issues</h2>
  <table><thead><tr><th>severity</th><th>kind</th><th>message</th></tr></thead><tbody>{issue_rows}</tbody></table>
  <h2>Guillotine Slicing</h2>
  <table><thead><tr><th>#</th><th>orientation</th><th>gap bbox um</th><th>lane width um</th><th>gap width um</th><th>split counts</th></tr></thead><tbody>{cut_rows}</tbody></table>
  <h2>Designs</h2>
  <table><thead><tr><th>name</th><th>bbox um</th><th>rotation</th><th>anchor</th><th>placeholder</th></tr></thead><tbody>{design_rows}</tbody></table>
</body>
</html>
"""


def _write_preview_png(
    path: Path,
    config: ProjectConfig,
    designs: list[PreviewDesign],
    issues: list[PreviewIssue],
    cuts: list[PreviewCut],
) -> None:
    mpw = config.mpw.bbox
    margin = 44
    top_margin = 82
    bottom_margin = 42
    side_w = 360
    max_plot = 1050
    scale = min(max_plot / mpw.width, max_plot / mpw.height)
    plot_w = max(1, int(round(mpw.width * scale)))
    plot_h = max(1, int(round(mpw.height * scale)))
    width = plot_w + side_w + margin * 2
    height = max(plot_h + top_margin + bottom_margin, 620)
    pixels = bytearray([248, 250, 252] * width * height)

    def sx(value: float) -> int:
        return int(round(margin + (value - mpw.xmin) * scale))

    def sy(value: float) -> int:
        return int(round(top_margin + (mpw.ymax - value) * scale))

    def draw_rect(bbox: BBox, color: tuple[int, int, int], alpha: float = 1.0, outline: tuple[int, int, int] | None = None) -> None:
        x0 = _clamp(sx(bbox.xmin), 0, width - 1)
        x1 = _clamp(sx(bbox.xmax), 0, width)
        y0 = _clamp(sy(bbox.ymax), 0, height - 1)
        y1 = _clamp(sy(bbox.ymin), 0, height)
        for y in range(y0, y1):
            row = y * width * 3
            for x in range(x0, x1):
                offset = row + x * 3
                _blend_pixel(pixels, offset, color, alpha)
        if outline is not None:
            _draw_outline(pixels, width, height, x0, y0, x1, y1, outline)

    _draw_text(pixels, width, height, margin, 16, "AUTOMPW PLACEMENT PREVIEW", (17, 24, 39), scale=3)
    summary = (
        f"MPW {mpw.width:.0f} X {mpw.height:.0f} UM  "
        f"DESIGNS {len(designs)}  UTIL {_utilization_text(config, designs)}  "
        f"SPACING {config.spacing_design_to_design_um:.1f} UM"
    )
    _draw_text(pixels, width, height, margin, 50, summary, (75, 85, 99), scale=2, max_width=plot_w + side_w)

    draw_rect(mpw, (255, 255, 255), outline=(17, 24, 39))
    for cut in cuts:
        draw_rect(cut.bbox, _hex_to_rgb(CUT_GAP_COLOR), alpha=0.48)
    for cut in cuts:
        draw_rect(_cut_lane_bbox(cut, config.spacing_design_to_design_um), _hex_to_rgb(CUT_LANE_COLOR), alpha=0.66)
    for item in designs:
        draw_rect(item.bbox, _hex_to_rgb(item.color), alpha=0.82, outline=(31, 41, 55))
    for issue in issues:
        if issue.bbox is not None:
            color = (239, 68, 68) if issue.kind in {"overlap", "outside"} else (245, 158, 11)
            draw_rect(issue.bbox, color, alpha=0.52, outline=color)
        elif issue.line_um is not None:
            x1, y1, x2, y2 = issue.line_um
            _draw_line(pixels, width, height, sx(x1), sy(y1), sx(x2), sy(y2), (245, 158, 11), thickness=4)

    for item in designs:
        x0 = sx(item.bbox.xmin) + 7
        y0 = sy(item.bbox.ymax) + 7
        chip_w = sx(item.bbox.xmax) - sx(item.bbox.xmin)
        chip_h = sy(item.bbox.ymin) - sy(item.bbox.ymax)
        text_scale = 2 if chip_w >= 90 and chip_h >= 42 else 1
        _draw_text(pixels, width, height, x0, y0, item.design.name, (17, 24, 39), scale=text_scale, max_width=max(1, chip_w - 12))
        if chip_h >= 58:
            detail = f"{item.bbox.width:.0f}X{item.bbox.height:.0f} R{item.design.rotation}"
            _draw_text(
                pixels,
                width,
                height,
                x0,
                y0 + 9 * text_scale,
                detail,
                (17, 24, 39),
                scale=1,
                max_width=max(1, chip_w - 12),
            )

    for index, cut in enumerate(cuts, start=1):
        label_x, label_y = _bbox_center(_cut_lane_bbox(cut, config.spacing_design_to_design_um))
        _draw_label_box(pixels, width, height, sx(label_x), sy(label_y), str(index))

    side_x = margin + plot_w + 24
    side_y = top_margin + 4
    _draw_text(pixels, width, height, side_x, side_y, "SUMMARY", (17, 24, 39), scale=2)
    side_y += 28
    for text in (
        f"UTIL {_utilization_text(config, designs)}",
        f"ISSUES {len(issues)}",
        f"CUTS {len(cuts)}" if cuts else "CUTS NONE",
    ):
        _draw_text(pixels, width, height, side_x, side_y, text, (75, 85, 99), scale=2, max_width=side_w - 30)
        side_y += 22

    side_y += 14
    _draw_text(pixels, width, height, side_x, side_y, "CUT ORDER", (17, 24, 39), scale=2)
    side_y += 28
    if cuts:
        for index, cut in enumerate(cuts[:12], start=1):
            gap = cut.bbox.width if cut.orientation == "vertical" else cut.bbox.height
            orient = "V" if cut.orientation == "vertical" else "H"
            text = f"#{index} {orient} LANE {config.spacing_design_to_design_um:.0f} GAP {gap:.0f}"
            _draw_text(pixels, width, height, side_x, side_y, text, (75, 85, 99), scale=1, max_width=side_w - 30)
            side_y += 14
    else:
        _draw_text(pixels, width, height, side_x, side_y, "NO SLICING TREE", (75, 85, 99), scale=1)
        side_y += 14

    side_y += 14
    _draw_text(pixels, width, height, side_x, side_y, "ISSUES", (17, 24, 39), scale=2)
    side_y += 28
    if issues:
        for issue in issues[:8]:
            _draw_text(pixels, width, height, side_x, side_y, f"{issue.kind}: {issue.severity}", (75, 85, 99), scale=1, max_width=side_w - 30)
            side_y += 14
    else:
        _draw_text(pixels, width, height, side_x, side_y, "NONE", (75, 85, 99), scale=1)
    _write_png(path, width, height, pixels)


def _write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        start = y * stride
        raw.extend(pixels[start : start + stride])
    compressed = zlib.compress(bytes(raw), level=6)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _cut_lane_bbox(cut: PreviewCut, lane_width_um: float) -> BBox:
    if cut.orientation == "vertical":
        width = min(max(lane_width_um, 0.0), cut.bbox.width)
        center = (cut.bbox.xmin + cut.bbox.xmax) / 2
        return BBox(center - width / 2, cut.bbox.ymin, center + width / 2, cut.bbox.ymax)
    height = min(max(lane_width_um, 0.0), cut.bbox.height)
    center = (cut.bbox.ymin + cut.bbox.ymax) / 2
    return BBox(cut.bbox.xmin, center - height / 2, cut.bbox.xmax, center + height / 2)


def _draw_text(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: object,
    color: tuple[int, int, int],
    scale: int = 1,
    max_width: int | None = None,
) -> None:
    cursor = x
    start_x = x
    for char in str(text).upper():
        pattern = FONT_5X7.get(char, FONT_5X7["?"])
        char_width = 5 * scale
        if max_width is not None and cursor + char_width - start_x > max_width:
            break
        for row, bits in enumerate(pattern):
            for col, bit in enumerate(bits):
                if bit == "1":
                    _draw_pixel_rect(
                        pixels,
                        width,
                        height,
                        cursor + col * scale,
                        y + row * scale,
                        cursor + (col + 1) * scale,
                        y + (row + 1) * scale,
                        color,
                    )
        cursor += 6 * scale


def _text_width(text: object, scale: int = 1) -> int:
    value = str(text)
    if not value:
        return 0
    return len(value) * 6 * scale - scale


def _draw_label_box(pixels: bytearray, width: int, height: int, center_x: int, center_y: int, text: object) -> None:
    scale = 2
    box_w = max(22, _text_width(text, scale=scale) + 10)
    box_h = 7 * scale + 8
    x0 = center_x - box_w // 2
    y0 = center_y - box_h // 2
    x1 = x0 + box_w
    y1 = y0 + box_h
    _draw_pixel_rect(pixels, width, height, x0, y0, x1, y1, _hex_to_rgb(CUT_LABEL_COLOR))
    _draw_outline(pixels, width, height, x0, y0, x1, y1, _hex_to_rgb(CUT_LABEL_TEXT_COLOR))
    _draw_text(
        pixels,
        width,
        height,
        x0 + max(1, (box_w - _text_width(text, scale=scale)) // 2),
        y0 + 4,
        text,
        _hex_to_rgb(CUT_LABEL_TEXT_COLOR),
        scale=scale,
    )


def _draw_pixel_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
    alpha: float = 1.0,
) -> None:
    x0 = _clamp(x0, 0, width)
    x1 = _clamp(x1, 0, width)
    y0 = _clamp(y0, 0, height)
    y1 = _clamp(y1, 0, height)
    if x1 <= x0 or y1 <= y0:
        return
    for row_y in range(y0, y1):
        row = row_y * width * 3
        for col_x in range(x0, x1):
            _blend_pixel(pixels, row + col_x * 3, color, alpha)


def _draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    half = max(0, thickness // 2)
    for index in range(steps + 1):
        x = round(x0 + (x1 - x0) * index / steps)
        y = round(y0 + (y1 - y0) * index / steps)
        _draw_pixel_rect(pixels, width, height, x - half, y - half, x + half + 1, y + half + 1, color)


def _spacing_marker(left: BBox, right: BBox) -> tuple[BBox | None, tuple[float, float, float, float] | None]:
    x_overlap_min = max(left.xmin, right.xmin)
    x_overlap_max = min(left.xmax, right.xmax)
    y_overlap_min = max(left.ymin, right.ymin)
    y_overlap_max = min(left.ymax, right.ymax)
    if y_overlap_max > y_overlap_min:
        if left.xmax <= right.xmin:
            if right.xmin > left.xmax:
                return BBox(left.xmax, y_overlap_min, right.xmin, y_overlap_max), None
            y_mid = (y_overlap_min + y_overlap_max) / 2
            return None, (left.xmax, y_mid, right.xmin, y_mid)
        if right.xmax <= left.xmin:
            if left.xmin > right.xmax:
                return BBox(right.xmax, y_overlap_min, left.xmin, y_overlap_max), None
            y_mid = (y_overlap_min + y_overlap_max) / 2
            return None, (right.xmax, y_mid, left.xmin, y_mid)
    if x_overlap_max > x_overlap_min:
        if left.ymax <= right.ymin:
            if right.ymin > left.ymax:
                return BBox(x_overlap_min, left.ymax, x_overlap_max, right.ymin), None
            x_mid = (x_overlap_min + x_overlap_max) / 2
            return None, (x_mid, left.ymax, x_mid, right.ymin)
        if right.ymax <= left.ymin:
            if left.ymin > right.ymax:
                return BBox(x_overlap_min, right.ymax, x_overlap_max, left.ymin), None
            x_mid = (x_overlap_min + x_overlap_max) / 2
            return None, (x_mid, right.ymax, x_mid, left.ymin)

    lx, ly = _bbox_center(left)
    rx, ry = _bbox_center(right)
    return None, (lx, ly, rx, ry)


def _intersection(left: BBox, right: BBox) -> BBox:
    return BBox(max(left.xmin, right.xmin), max(left.ymin, right.ymin), min(left.xmax, right.xmax), min(left.ymax, right.ymax))


def _bbox_center(bbox: BBox) -> tuple[float, float]:
    return (bbox.xmin + bbox.xmax) / 2, (bbox.ymin + bbox.ymax) / 2


def _issue_design_map(issues: list[PreviewIssue]) -> dict[str, str]:
    priority = {"clearance": 1, "outside": 2, "overlap": 3}
    result: dict[str, str] = {}
    for issue in issues:
        for name in issue.designs:
            current = result.get(name)
            if priority.get(issue.kind, 0) >= priority.get(current or "", 0):
                result[name] = issue.kind
    return result


def _fmt_bbox(bbox: BBox) -> str:
    return f"[{bbox.xmin:.3f}, {bbox.ymin:.3f}, {bbox.xmax:.3f}, {bbox.ymax:.3f}]"


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _blend_pixel(pixels: bytearray, offset: int, color: tuple[int, int, int], alpha: float) -> None:
    if alpha >= 1.0:
        pixels[offset : offset + 3] = bytes(color)
        return
    inv = 1.0 - alpha
    pixels[offset] = int(pixels[offset] * inv + color[0] * alpha)
    pixels[offset + 1] = int(pixels[offset + 1] * inv + color[1] * alpha)
    pixels[offset + 2] = int(pixels[offset + 2] * inv + color[2] * alpha)


def _draw_outline(
    pixels: bytearray,
    width: int,
    height: int,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    for x in range(max(0, x0), min(width, x1)):
        for y in (y0, y1 - 1):
            if 0 <= y < height:
                offset = (y * width + x) * 3
                pixels[offset : offset + 3] = bytes(color)
    for y in range(max(0, y0), min(height, y1)):
        for x in (x0, x1 - 1):
            if 0 <= x < width:
                offset = (y * width + x) * 3
                pixels[offset : offset + 3] = bytes(color)


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
