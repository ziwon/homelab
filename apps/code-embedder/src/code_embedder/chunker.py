from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    start_line: int
    end_line: int
    chunk_id: int


def chunk_text(text: str, max_lines: int, overlap_lines: int) -> list[Chunk]:
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")

    lines = text.splitlines()
    if not lines:
        return []

    overlap = max(0, min(overlap_lines, max_lines - 1))
    step = max_lines - overlap

    chunks: list[Chunk] = []
    chunk_id = 0
    for start in range(0, len(lines), step):
        end = min(start + max_lines, len(lines))
        chunk_lines = lines[start:end]
        chunk_text_value = "\n".join(chunk_lines)
        chunks.append(
            Chunk(
                text=chunk_text_value,
                start_line=start + 1,
                end_line=end,
                chunk_id=chunk_id,
            )
        )
        chunk_id += 1

    return chunks
