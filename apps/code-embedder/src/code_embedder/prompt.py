from __future__ import annotations

from typing import Iterable

from jinja2 import Template

from code_embedder.config import Config
from code_embedder.search import SearchHit


def render_prompt(config: Config, hits: Iterable[SearchHit], issue_description: str) -> str:
    template = Template(config.prompt_template)
    chunks = []
    for hit in list(hits)[: config.prompt_max_chunks]:
        payload = hit.payload or {}
        chunks.append(
            {
                "file_path": payload.get("path", ""),
                "language": payload.get("lang", ""),
                "structure": payload.get("structure", ""),
                "class_name": payload.get("class_name", ""),
                "function_name": payload.get("function_name", ""),
                "app_name": payload.get("app_name", ""),
                "app_namespace": payload.get("app_namespace", ""),
                "chart_name": payload.get("chart_name", ""),
                "yaml_path": payload.get("yaml_path", ""),
                "embedded_kind": payload.get("embedded_kind", ""),
                "embedded_name": payload.get("embedded_name", ""),
                "block_key": payload.get("block_key", ""),
                "score": hit.score,
                "code_content": payload.get(config.text_field, ""),
            }
        )
    return template.render(chunks=chunks, issue_description=issue_description)
