from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def template_root() -> Path:
    override = os.environ.get("AUTOMPW_TEMPLATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    candidates = [
        Path(__file__).resolve().parent.parent / "templates",
        Path(sys.prefix) / "templates",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def available_processes() -> list[str]:
    root = template_root()
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def init_process(process: str, destination: Path) -> Path:
    source = template_root() / process
    if not source.is_dir():
        choices = ", ".join(available_processes()) or "<none>"
        raise ValueError(f"Unknown process {process!r}. Available processes: {choices}")

    source_config = source / "mpw_config.yaml"
    source_deck = source / "deck"
    if not source_config.is_file():
        raise FileNotFoundError(f"Template config not found: {source_config}")
    if not source_deck.is_dir():
        raise FileNotFoundError(f"Template deck directory not found: {source_deck}")

    target_config = destination / "mpw_config.yaml"
    target_deck = destination / "deck"
    _ensure_absent(target_config)
    _ensure_absent(target_deck)

    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_config, target_config)
    shutil.copytree(source_deck, target_deck)
    for dirname in ("input", "output", "work"):
        (destination / dirname).mkdir(exist_ok=True)
    return target_config


def _ensure_absent(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing path: {path}")
