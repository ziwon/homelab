from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from code_embedder.app_of_apps import AppChunk, parse_app_of_apps
from code_embedder.chunker import chunk_text
from code_embedder.config import Config
from code_embedder.embedder import embed_texts
from code_embedder.filters import is_binary_file, should_include
from code_embedder.git_diff import get_changed_files, get_head_commit
from code_embedder.qdrant import QdrantClient, ensure_collection
from code_embedder.structure import extract_structure_hint
from code_embedder.yaml_blocks import extract_yaml_block_scalars

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
}


@dataclass(frozen=True)
class IndexStats:
    commit: str
    files_indexed: int
    files_deleted: int
    chunks_indexed: int
    bytes_indexed: int


@dataclass(frozen=True)
class EmbedItem:
    text: str
    structure_hint: str
    app_name: str | None
    app_namespace: str | None
    chart_name: str | None
    yaml_path: str | None
    embedded_kind: str | None
    embedded_name: str | None
    block_key: str | None


@dataclass(frozen=True)
class EmbedChunk:
    text: str
    start_line: int
    end_line: int
    chunk_id: int
    app_name: str | None
    app_namespace: str | None
    chart_name: str | None
    yaml_path: str | None
    embedded_kind: str | None
    embedded_name: str | None
    block_key: str | None


def main() -> int:
    config = Config.load()
    run_index(config)
    return 0


def run_index(config: Config) -> IndexStats:
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if config.vector_size is not None:
        logging.info("Configured vector size: %s", config.vector_size)

    client = QdrantClient.from_config(config)
    commit = config.commit_sha or get_head_commit(config.repo_path) or "unknown"

    if config.full_reindex:
        changed_files = _list_all_files(config)
        deleted_files: set[str] = set()
    else:
        changed_files, deleted_files = get_changed_files(config)

    changed_paths = _filter_paths(config, changed_files)
    files_deleted = 0
    if config.enable_delete:
        delete_targets = set(deleted_files)
        delete_targets.update(changed_paths)
        if delete_targets:
            _log_paths("deleting", delete_targets)
            files_deleted = len(delete_targets)
            if not config.dry_run:
                client.delete_by_paths(config.qdrant_collection, config.repo_name, delete_targets)

    if not changed_paths:
        logging.info("No files to index.")
        return IndexStats(
            commit=commit,
            files_indexed=0,
            files_deleted=files_deleted,
            chunks_indexed=0,
            bytes_indexed=0,
        )

    collection_ready = False
    files_indexed = 0
    chunks_indexed = 0
    bytes_indexed = 0
    for rel_path in sorted(changed_paths):
        full_path = config.repo_path / rel_path
        if not full_path.exists():
            continue
        if full_path.stat().st_size > config.max_file_bytes:
            logging.info("Skipping large file: %s", rel_path)
            continue
        if is_binary_file(full_path):
            logging.info("Skipping binary file: %s", rel_path)
            continue

        file_text = full_path.read_text(encoding="utf-8", errors="ignore")
        chunks = _build_chunks(config, rel_path, file_text)
        if not chunks:
            continue

        file_hash = _hash_text(file_text)
        lang = _detect_language(full_path)
        files_indexed += 1
        bytes_indexed += len(file_text.encode("utf-8"))

        for batch in _batch_chunks(chunks, config.embed_batch_size):
            embed_items = [
                _build_embed_item(
                    config=config,
                    rel_path=rel_path,
                    lang=lang,
                    chunk=chunk,
                )
                for chunk in batch
            ]
            embeddings = embed_texts(config, [item.text for item in embed_items])
            if not collection_ready:
                vector_size = len(embeddings[0])
                logging.info("Embedding vector size: %s", vector_size)
                ensure_collection(client, config, vector_size)
                collection_ready = True

            points = _build_points(
                config=config,
                rel_path=rel_path,
                commit=commit,
                lang=lang,
                file_hash=file_hash,
                chunks=batch,
                embeddings=embeddings,
                structure_hints=[item.structure_hint for item in embed_items],
                app_names=[item.app_name for item in embed_items],
                app_namespaces=[item.app_namespace for item in embed_items],
                chart_names=[item.chart_name for item in embed_items],
                yaml_paths=[item.yaml_path for item in embed_items],
                embedded_kinds=[item.embedded_kind for item in embed_items],
                embedded_names=[item.embedded_name for item in embed_items],
                block_keys=[item.block_key for item in embed_items],
            )
            chunks_indexed += len(points)

            if config.dry_run:
                logging.info("Dry run upsert: %s chunks", len(points))
                continue

            for points_batch in _batch_list(points, config.qdrant_batch_size):
                client.upsert_points(config.qdrant_collection, points_batch)

    return IndexStats(
        commit=commit,
        files_indexed=files_indexed,
        files_deleted=files_deleted,
        chunks_indexed=chunks_indexed,
        bytes_indexed=bytes_indexed,
    )


def _list_all_files(config: Config) -> set[str]:
    paths: set[str] = set()
    for path in config.repo_path.rglob("*"):
        if not should_include(path, config):
            continue
        rel = path.relative_to(config.repo_path).as_posix()
        paths.add(rel)
    return paths


def _filter_paths(config: Config, paths: Iterable[str]) -> set[str]:
    filtered: set[str] = set()
    for rel_path in paths:
        full_path = config.repo_path / rel_path
        if should_include(full_path, config):
            filtered.add(rel_path)
    return filtered


def _detect_language(path: Path) -> str:
    if path.name in {"Dockerfile", "Containerfile"}:
        return "docker"
    if path.name in {"Makefile", "Justfile"}:
        return "build"
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "text")


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _hash_chunk(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _build_points(
    *,
    config: Config,
    rel_path: str,
    commit: str,
    lang: str,
    file_hash: str,
    chunks: list[EmbedChunk],
    embeddings: list[list[float]],
    structure_hints: list[str],
    app_names: list[str | None],
    app_namespaces: list[str | None],
    chart_names: list[str | None],
    yaml_paths: list[str | None],
    embedded_kinds: list[str | None],
    embedded_names: list[str | None],
    block_keys: list[str | None],
) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    points: list[dict] = []

    for chunk, embedding, structure_hint, app_name, app_namespace, chart_name, yaml_path, embedded_kind, embedded_name, block_key in zip(  # noqa: E501
        chunks,
        embeddings,
        structure_hints,
        app_names,
        app_namespaces,
        chart_names,
        yaml_paths,
        embedded_kinds,
        embedded_names,
        block_keys,
        strict=True,
    ):
        chunk_hash = _hash_chunk(chunk.text)
        hash_hex = hashlib.sha1(
            f"{config.repo_name}:{rel_path}:{chunk.chunk_id}:{chunk_hash}".encode("utf-8")
        ).hexdigest()
        point_id = str(uuid.UUID(hash_hex[:32]))
        payload = {
            "repo": config.repo_name,
            "path": rel_path,
            "lang": lang,
            "commit": commit,
            "chunk_id": chunk.chunk_id,
            "file_hash": file_hash,
            "chunk_hash": chunk_hash,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "updated_at": now,
        }
        if structure_hint:
            payload["structure"] = structure_hint
        if app_name:
            payload["app_name"] = app_name
        if app_namespace:
            payload["app_namespace"] = app_namespace
        if chart_name:
            payload["chart_name"] = chart_name
        if yaml_path:
            payload["yaml_path"] = yaml_path
        if embedded_kind:
            payload["embedded_kind"] = embedded_kind
        if embedded_name:
            payload["embedded_name"] = embedded_name
        if block_key:
            payload["block_key"] = block_key
        if config.store_text:
            payload[config.text_field] = chunk.text
        points.append({"id": point_id, "vector": embedding, "payload": payload})

    return points


def _batch_chunks(chunks: list[EmbedChunk], size: int) -> Iterable[list[EmbedChunk]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    for index in range(0, len(chunks), size):
        yield chunks[index : index + size]


def _batch_list(items: list[dict], size: int) -> Iterable[list[dict]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _log_paths(label: str, paths: Iterable[str]) -> None:
    for path in sorted(paths):
        logging.info("%s: %s", label, path)


def _build_embed_item(
    *,
    config: Config,
    rel_path: str,
    lang: str,
    chunk: EmbedChunk,
) -> EmbedItem:
    structure_hint = _structure_hint(
        config=config,
        rel_path=rel_path,
        chunk=chunk,
    )
    context = _format_context(
        config=config,
        rel_path=rel_path,
        lang=lang,
        chunk=chunk,
        structure_hint=structure_hint,
    )
    parts: list[str] = []
    if config.embed_text_prefix:
        parts.append(config.embed_text_prefix)
    if context:
        parts.append(context)
    parts.append(chunk.text)
    return EmbedItem(
        text="".join(parts),
        structure_hint=structure_hint,
        app_name=chunk.app_name,
        app_namespace=chunk.app_namespace,
        chart_name=chunk.chart_name,
        yaml_path=chunk.yaml_path,
        embedded_kind=chunk.embedded_kind,
        embedded_name=chunk.embedded_name,
        block_key=chunk.block_key,
    )


def _format_context(
    *,
    config: Config,
    rel_path: str,
    lang: str,
    chunk: EmbedChunk,
    structure_hint: str,
) -> str:
    template = config.context_template
    if not template.strip():
        return ""
    try:
        return template.format(
            repo=config.repo_name,
            path=rel_path,
            lang=lang,
            structure=structure_hint,
            app_name=chunk.app_name or "",
            app_namespace=chunk.app_namespace or "",
            chart_name=chunk.chart_name or "",
            yaml_path=chunk.yaml_path or "",
            embedded_kind=chunk.embedded_kind or "",
            embedded_name=chunk.embedded_name or "",
            block_key=chunk.block_key or "",
            chunk_id=chunk.chunk_id,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
        )
    except (KeyError, ValueError) as exc:
        logging.warning("Invalid CONTEXT_TEMPLATE: %s", exc)
        return ""


def _structure_hint(*, config: Config, rel_path: str, chunk: EmbedChunk) -> str:
    if not config.include_structure_hints:
        return ""
    return extract_structure_hint(
        rel_path=rel_path,
        text=chunk.text,
        max_items=config.structure_max_items,
        max_chars=config.structure_max_chars,
    )


def _build_chunks(config: Config, rel_path: str, file_text: str) -> list[EmbedChunk]:
    if rel_path.endswith((".yaml", ".yml")):
        app_chunks = parse_app_of_apps(
            file_path=rel_path,
            yaml_content=file_text,
            chunk_max_lines=config.chunk_max_lines,
            chunk_overlap_lines=config.chunk_overlap_lines,
        )
        if app_chunks:
            return [_from_app_chunk(chunk) for chunk in app_chunks]

    base_chunks = [
        EmbedChunk(
            text=chunk.text,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            chunk_id=chunk.chunk_id,
            app_name=None,
            app_namespace=None,
            chart_name=None,
            yaml_path=None,
            embedded_kind=None,
            embedded_name=None,
            block_key=None,
        )
        for chunk in chunk_text(file_text, config.chunk_max_lines, config.chunk_overlap_lines)
    ]
    if rel_path.endswith((".yaml", ".yml")):
        base_chunks.extend(_yaml_block_chunks(config, file_text, offset=len(base_chunks)))
    return base_chunks


def _from_app_chunk(chunk: AppChunk) -> EmbedChunk:
    return EmbedChunk(
        text=chunk.text,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        chunk_id=chunk.chunk_id,
        app_name=chunk.app_name,
        app_namespace=chunk.app_namespace,
        chart_name=chunk.chart_name,
        yaml_path=chunk.yaml_path,
        embedded_kind=chunk.embedded_kind,
        embedded_name=chunk.embedded_name,
        block_key=chunk.block_key,
    )


def _yaml_block_chunks(config: Config, file_text: str, offset: int) -> list[EmbedChunk]:
    chunks: list[EmbedChunk] = []
    chunk_id = offset
    blocks = extract_yaml_block_scalars(file_text)
    for block in blocks:
        for chunk in chunk_text(block.text, config.chunk_max_lines, config.chunk_overlap_lines):
            chunks.append(
                EmbedChunk(
                    text=chunk.text,
                    start_line=block.start_line + chunk.start_line - 1,
                    end_line=block.start_line + chunk.end_line - 1,
                    chunk_id=chunk_id,
                    app_name=None,
                    app_namespace=None,
                    chart_name=None,
                    yaml_path=f"block[key={block.key}]",
                    embedded_kind=None,
                    embedded_name=None,
                    block_key=block.key,
                )
            )
            chunk_id += 1
    return chunks
