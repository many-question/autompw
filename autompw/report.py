from __future__ import annotations

from dataclasses import dataclass

from .config import ProjectConfig


@dataclass(frozen=True)
class CheckIssue:
    severity: str
    message: str


def check_project(config: ProjectConfig) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    mpw_bbox = config.mpw.bbox

    for design in config.designs:
        bbox = design.bbox
        if not mpw_bbox.contains(bbox):
            issues.append(
                CheckIssue(
                    "error",
                    f"{design.name} bbox {bbox.as_list()} is outside MPW bbox {mpw_bbox.as_list()}",
                )
            )

    for i, left in enumerate(config.designs):
        for right in config.designs[i + 1 :]:
            left_bbox = left.bbox
            right_bbox = right.bbox
            if left_bbox.overlaps(right_bbox):
                issues.append(
                    CheckIssue(
                        "error",
                        f"{left.name} bbox {left_bbox.as_list()} overlaps {right.name} bbox {right_bbox.as_list()}",
                    )
                )
                continue
            spacing = left_bbox.spacing_to(right_bbox)
            if spacing < config.spacing_design_to_design_um:
                issues.append(
                    CheckIssue(
                        "error",
                        f"{left.name} to {right.name} spacing {spacing:.3f}um is below {config.spacing_design_to_design_um:.3f}um",
                    )
                )

    return issues
