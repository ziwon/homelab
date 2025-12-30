from __future__ import annotations

from pathlib import Path
from typing import Iterable

from code_embedder.config import Config


def should_include(path: Path, config: Config) -> bool:
    if not path.is_file():
        return False

    rel = path.relative_to(config.repo_path)
    if _is_excluded(rel.parts, config.exclude_dirs):
        return False

    if path.name in config.include_files:
        return True

    suffix = path.suffix.lower()
    return suffix in config.include_extensions


def _is_excluded(parts: Iterable[str], exclude_dirs: Iterable[str]) -> bool:
    exclude_set = set(exclude_dirs)
    return any(part in exclude_set for part in parts)


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(2048)
    except OSError:
        return True
    return b"\0" in chunk
