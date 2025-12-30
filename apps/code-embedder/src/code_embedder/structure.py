from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import re


_YAML_KEY_RE = re.compile(r"^(\s*)(-\s*)?([A-Za-z0-9_.-]+):")
_JSON_KEY_RE = re.compile(r"\"([A-Za-z0-9_.-]+)\"\s*:")


def extract_structure_hint(
    *,
    rel_path: str,
    text: str,
    max_items: int,
    max_chars: int,
) -> str:
    extension = Path(rel_path).suffix.lower()
    if extension in {".yaml", ".yml"}:
        items = _extract_yaml_paths(text, max_items)
    elif extension == ".json":
        items = _extract_json_keys(text, max_items)
    else:
        return ""

    if not items:
        return ""

    hint = ", ".join(items)
    if len(hint) <= max_chars:
        return hint
    return f"{hint[:max_chars].rstrip()}..."


def _extract_yaml_paths(text: str, max_items: int) -> list[str]:
    paths: "OrderedDict[str, None]" = OrderedDict()
    stack: list[tuple[int, str]] = []

    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _YAML_KEY_RE.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        key = match.group(3)

        while stack and indent <= stack[-1][0]:
            stack.pop()

        path = "/".join([item[1] for item in stack] + [key])
        paths.setdefault(path, None)
        stack.append((indent, key))

        if len(paths) >= max_items:
            break

    return list(paths.keys())


def _extract_json_keys(text: str, max_items: int) -> list[str]:
    keys: "OrderedDict[str, None]" = OrderedDict()
    for match in _JSON_KEY_RE.finditer(text):
        key = match.group(1)
        keys.setdefault(key, None)
        if len(keys) >= max_items:
            break
    return list(keys.keys())
