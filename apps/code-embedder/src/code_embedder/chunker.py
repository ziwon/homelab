from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    start_line: int
    end_line: int
    chunk_id: int


def chunk_text(text: str, max_lines: int, overlap_lines: int, max_chars: int | None = None) -> list[Chunk]:
    if max_lines <= 0:
        raise ValueError("max_lines must be positive")
    if max_chars is not None and max_chars <= 0:
        raise ValueError("max_chars must be positive when set")

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
        if max_chars is None:
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
            continue

        for piece_text, piece_start, piece_end in _split_lines_by_chars(
            chunk_lines,
            start_line=start + 1,
            max_chars=max_chars,
        ):
            chunks.append(
                Chunk(
                    text=piece_text,
                    start_line=piece_start,
                    end_line=piece_end,
                    chunk_id=chunk_id,
                )
            )
            chunk_id += 1

    return chunks


def _split_lines_by_chars(
    lines: list[str],
    *,
    start_line: int,
    max_chars: int,
) -> list[tuple[str, int, int]]:
    pieces: list[tuple[str, int, int]] = []
    current_lines: list[str] = []
    current_len = 0
    current_start = start_line
    current_end = start_line - 1

    for index, line in enumerate(lines):
        line_no = start_line + index
        if len(line) > max_chars:
            if current_lines:
                pieces.append(("\n".join(current_lines), current_start, current_end))
                current_lines = []
                current_len = 0
            for offset in range(0, len(line), max_chars):
                segment = line[offset : offset + max_chars]
                pieces.append((segment, line_no, line_no))
            current_start = line_no + 1
            current_end = line_no
            continue

        add_len = len(line) + (1 if current_lines else 0)
        if current_lines and current_len + add_len > max_chars:
            pieces.append(("\n".join(current_lines), current_start, current_end))
            current_lines = [line]
            current_len = len(line)
            current_start = line_no
            current_end = line_no
            continue

        if not current_lines:
            current_start = line_no
        current_lines.append(line)
        current_len += add_len
        current_end = line_no

    if current_lines:
        pieces.append(("\n".join(current_lines), current_start, current_end))

    return pieces
