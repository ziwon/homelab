from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class YamlBlock:
    key: str
    text: str
    start_line: int
    end_line: int


_BLOCK_KEY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[^:#\n]+):\s*(?P<marker>[|>][+-]?\d*)\s*(#.*)?$"
)
_BLOCK_LIST_RE = re.compile(
    r"^(?P<indent>\s*)-\s*(?P<marker>[|>][+-]?\d*)\s*(#.*)?$"
)


def extract_yaml_block_scalars(text: str) -> list[YamlBlock]:
    lines = text.splitlines()
    blocks: list[YamlBlock] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        match = _BLOCK_KEY_RE.match(line)
        key = None
        if match:
            key = match.group("key").strip().strip("\"'")
        else:
            match = _BLOCK_LIST_RE.match(line)
            if match:
                key = "list_item"

        if not match:
            index += 1
            continue

        content_start = index + 1
        content_indent = _find_block_indent(lines, content_start)
        if content_indent is None:
            index += 1
            continue

        content_lines: list[str] = []
        last_line = content_start
        cursor = content_start
        while cursor < len(lines):
            current = lines[cursor]
            if current.strip() == "":
                content_lines.append("")
                last_line = cursor
                cursor += 1
                continue

            current_indent = len(current) - len(current.lstrip(" "))
            if current_indent < content_indent:
                break

            content_lines.append(current[content_indent:])
            last_line = cursor
            cursor += 1

        block_text = "\n".join(content_lines).rstrip()
        if block_text:
            blocks.append(
                YamlBlock(
                    key=key or "block",
                    text=block_text,
                    start_line=content_start + 1,
                    end_line=last_line + 1,
                )
            )

        index = max(cursor, index + 1)

    return blocks


def _find_block_indent(lines: list[str], start_index: int) -> int | None:
    for cursor in range(start_index, len(lines)):
        line = lines[cursor]
        if line.strip() == "":
            continue
        return len(line) - len(line.lstrip(" "))
    return None
