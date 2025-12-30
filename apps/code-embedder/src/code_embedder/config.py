from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

DEFAULT_INCLUDE_EXTENSIONS = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
)

DEFAULT_INCLUDE_FILES = (
    "Dockerfile",
    "Containerfile",
    "Makefile",
    "Justfile",
)

DEFAULT_EXCLUDE_DIRS = (
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "coverage",
    "site-packages",
)


def _split_csv(value: str) -> tuple[str, ...]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    return tuple(items)


def _normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        if not value:
            continue
        if value.startswith("."):
            normalized.append(value.lower())
        else:
            normalized.append(f".{value.lower()}")
    return tuple(normalized)


def _get_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Config:
    repo_path: Path
    repo_name: str
    qdrant_url: str
    qdrant_api_key: str | None
    qdrant_collection: str
    vector_size: int | None
    vector_distance: str
    store_text: bool
    text_field: str
    create_text_index: bool
    include_structure_hints: bool
    structure_max_items: int
    structure_max_chars: int
    embed_api_url: str
    embed_api_key: str | None
    embed_model: str | None
    embed_batch_size: int
    embed_timeout: int
    embed_text_prefix: str
    context_template: str
    query_text_prefix: str
    prompt_template: str
    prompt_max_chunks: int
    qdrant_batch_size: int
    qdrant_timeout: int
    include_extensions: tuple[str, ...]
    include_files: tuple[str, ...]
    exclude_dirs: tuple[str, ...]
    max_file_bytes: int
    chunk_max_lines: int
    chunk_overlap_lines: int
    full_reindex: bool
    enable_delete: bool
    dry_run: bool
    commit_sha: str | None
    git_base_ref: str | None
    git_head_ref: str | None
    log_level: str

    @classmethod
    def load(cls) -> "Config":
        repo_path = Path(os.getenv("REPO_PATH", ".")).resolve()
        repo_name = os.getenv("REPO_NAME") or repo_path.name

        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333").rstrip("/")
        qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
        qdrant_collection = os.getenv("QDRANT_COLLECTION", "codebase-bge-m3")

        vector_size_value = os.getenv("VECTOR_SIZE")
        vector_size = int(vector_size_value) if vector_size_value else None
        vector_distance = os.getenv("VECTOR_DISTANCE", "Cosine")

        store_text = _get_bool(os.getenv("STORE_TEXT"), True)
        text_field = os.getenv("TEXT_FIELD", "text")
        create_text_index = _get_bool(os.getenv("CREATE_TEXT_INDEX"), store_text)
        include_structure_hints = _get_bool(os.getenv("INCLUDE_STRUCTURE_HINTS"), True)
        structure_max_items = int(os.getenv("STRUCTURE_MAX_ITEMS", "16"))
        structure_max_chars = int(os.getenv("STRUCTURE_MAX_CHARS", "800"))

        embed_api_url = _resolve_embed_url()
        embed_api_key = os.getenv("EMBED_API_KEY") or None
        embed_model = os.getenv("EMBED_MODEL") or None
        embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "16"))
        embed_timeout = int(os.getenv("EMBED_TIMEOUT", "60"))
        embed_text_prefix = os.getenv("EMBED_TEXT_PREFIX", "passage: ")
        context_template = os.getenv(
            "CONTEXT_TEMPLATE",
            "path: {path}\nlang: {lang}\nstructure: {structure}\nblock_key: {block_key}\n\n",
        )
        query_text_prefix = os.getenv("QUERY_TEXT_PREFIX", "query: ")
        prompt_template = _load_prompt_template(
            os.getenv(
                "PROMPT_TEMPLATE",
                "<relevant_code_files>\n"
                "{% for chunk in chunks %}\n"
                "<file_context id=\"{{ loop.index }}\">\n"
                "<metadata>\n"
                "<path>{{ chunk.file_path }}</path>\n"
                "<language>{{ chunk.language }}</language>\n"
                "<relevance_score>{{ chunk.score | round(4) }}</relevance_score>\n"
                "</metadata>\n"
                "<content>\n"
                "{{ chunk.code_content }}\n"
                "</content>\n"
                "</file_context>\n"
                "{% endfor %}\n"
                "</relevant_code_files>\n",
            )
        )
        prompt_max_chunks = int(os.getenv("PROMPT_MAX_CHUNKS", "12"))

        qdrant_batch_size = int(os.getenv("QDRANT_BATCH_SIZE", "64"))
        qdrant_timeout = int(os.getenv("QDRANT_TIMEOUT", "30"))

        include_extensions_value = os.getenv("INCLUDE_EXTENSIONS")
        if include_extensions_value:
            include_extensions = _normalize_extensions(_split_csv(include_extensions_value))
        else:
            include_extensions = DEFAULT_INCLUDE_EXTENSIONS

        include_files_value = os.getenv("INCLUDE_FILES")
        if include_files_value:
            include_files = _split_csv(include_files_value)
        else:
            include_files = DEFAULT_INCLUDE_FILES

        exclude_dirs_value = os.getenv("EXCLUDE_DIRS")
        if exclude_dirs_value:
            exclude_dirs = _split_csv(exclude_dirs_value)
        else:
            exclude_dirs = DEFAULT_EXCLUDE_DIRS

        max_file_bytes = int(os.getenv("MAX_FILE_BYTES", "1000000"))
        chunk_max_lines = int(os.getenv("CHUNK_MAX_LINES", "200"))
        chunk_overlap_lines = int(os.getenv("CHUNK_OVERLAP_LINES", "20"))

        full_reindex = _get_bool(os.getenv("FULL_REINDEX"), False)
        enable_delete = _get_bool(os.getenv("ENABLE_DELETE"), True)
        dry_run = _get_bool(os.getenv("DRY_RUN"), False)

        commit_sha = os.getenv("COMMIT_SHA") or None
        git_base_ref = os.getenv("GIT_BASE_REF") or None
        git_head_ref = os.getenv("GIT_HEAD_REF") or None

        log_level = os.getenv("LOG_LEVEL", "INFO")

        return cls(
            repo_path=repo_path,
            repo_name=repo_name,
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
            qdrant_collection=qdrant_collection,
            vector_size=vector_size,
            vector_distance=vector_distance,
            store_text=store_text,
            text_field=text_field,
            create_text_index=create_text_index,
            include_structure_hints=include_structure_hints,
            structure_max_items=structure_max_items,
            structure_max_chars=structure_max_chars,
            embed_api_url=embed_api_url,
            embed_api_key=embed_api_key,
            embed_model=embed_model,
            embed_batch_size=embed_batch_size,
            embed_timeout=embed_timeout,
            embed_text_prefix=embed_text_prefix,
            context_template=context_template,
            query_text_prefix=query_text_prefix,
            prompt_template=prompt_template,
            prompt_max_chunks=prompt_max_chunks,
            qdrant_batch_size=qdrant_batch_size,
            qdrant_timeout=qdrant_timeout,
            include_extensions=include_extensions,
            include_files=include_files,
            exclude_dirs=exclude_dirs,
            max_file_bytes=max_file_bytes,
            chunk_max_lines=chunk_max_lines,
            chunk_overlap_lines=chunk_overlap_lines,
            full_reindex=full_reindex,
            enable_delete=enable_delete,
            dry_run=dry_run,
            commit_sha=commit_sha,
            git_base_ref=git_base_ref,
            git_head_ref=git_head_ref,
            log_level=log_level,
        )


def _resolve_embed_url() -> str:
    explicit = os.getenv("EMBED_API_URL")
    if explicit:
        return explicit

    raw = os.getenv("LLM_EMBED_URL", "http://llama-cpp-embed:8080")
    raw = raw.rstrip("/")
    if raw.endswith("/v1/embeddings") or raw.endswith("/embedding"):
        return raw
    return f"{raw}/v1/embeddings"


def _load_prompt_template(default_template: str) -> str:
    template_path = os.getenv("PROMPT_TEMPLATE_PATH")
    if not template_path:
        return default_template
    return Path(template_path).read_text(encoding="utf-8")
