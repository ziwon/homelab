from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from code_embedder.chunker import chunk_text
from code_embedder.yaml_blocks import extract_yaml_block_scalars


@dataclass(frozen=True)
class AppChunk:
    text: str
    start_line: int
    end_line: int
    chunk_id: int
    app_name: str
    app_namespace: str
    chart_name: str
    yaml_path: str
    embedded_kind: str | None
    embedded_name: str | None
    block_key: str | None


def parse_app_of_apps(
    *,
    file_path: str,
    yaml_content: str,
    chunk_max_lines: int,
    chunk_overlap_lines: int,
    chunk_max_chars: int | None,
) -> list[AppChunk]:
    data = _safe_load_yaml(yaml_content)
    if not isinstance(data, dict):
        return []

    apps = data.get("apps")
    if not isinstance(apps, list):
        return []

    chunks: list[AppChunk] = []
    chunk_id = 0

    for app in apps:
        if not isinstance(app, dict):
            continue

        app_name = str(app.get("name", "unknown"))
        app_namespace = str(app.get("namespace", "default"))
        source = app.get("source") if isinstance(app.get("source"), dict) else {}
        chart_name = _resolve_chart_name(source)

        app_yaml = _dump_yaml(app)
        chunk_id = _append_chunks(
            chunks,
            chunk_id,
            app_yaml,
            app_name,
            app_namespace,
            chart_name,
            f"apps[name={app_name}]",
            None,
            None,
            chunk_max_lines,
            chunk_overlap_lines,
            chunk_max_chars,
        )
        chunk_id = _append_block_chunks(
            chunks,
            chunk_id,
            app_yaml,
            app_name,
            app_namespace,
            chart_name,
            f"apps[name={app_name}]",
            None,
            None,
            chunk_max_lines,
            chunk_overlap_lines,
            skip_keys={"values"},
            chunk_max_chars=chunk_max_chars,
        )

        if chart_name == "kustomize":
            kustomize_block: dict[str, Any] = {}
            if isinstance(source, dict):
                if "path" in source:
                    kustomize_block["path"] = source.get("path")
                if "kustomize" in source:
                    kustomize_block["kustomize"] = source.get("kustomize")
            if kustomize_block:
                kustomize_yaml = _dump_yaml(kustomize_block)
                chunk_id = _append_chunks(
                    chunks,
                    chunk_id,
                    kustomize_yaml,
                    app_name,
                    app_namespace,
                    chart_name,
                    f"apps[name={app_name}].source.kustomize",
                    None,
                    None,
                    chunk_max_lines,
                    chunk_overlap_lines,
                    block_key="kustomize",
                    chunk_max_chars=chunk_max_chars,
                )

        values = None
        helm = source.get("helm") if isinstance(source, dict) else None
        if isinstance(helm, dict):
            values = helm.get("values")

        if values is None:
            continue

        if isinstance(values, dict):
            values_str = _dump_yaml(values)
            inner_values = values
        else:
            values_str = str(values)
            inner_values = _safe_load_yaml(values_str)

        if chart_name == "raw" and isinstance(inner_values, dict):
            resources = inner_values.get("resources")
            if isinstance(resources, list):
                for idx, res in enumerate(resources):
                    if not isinstance(res, dict):
                        continue
                    kind = str(res.get("kind", "Unknown"))
                    name = str(res.get("metadata", {}).get("name", "Unknown"))
                    res_yaml = _dump_yaml(res)
                    chunk_id = _append_chunks(
                        chunks,
                        chunk_id,
                        res_yaml,
                        app_name,
                        app_namespace,
                        chart_name,
                        f"apps[name={app_name}].helm.values.resources[{idx}]",
                        kind,
                        name,
                        chunk_max_lines,
                        chunk_overlap_lines,
                        block_key="values",
                        chunk_max_chars=chunk_max_chars,
                    )
                    chunk_id = _append_block_chunks(
                        chunks,
                        chunk_id,
                        res_yaml,
                        app_name,
                        app_namespace,
                        chart_name,
                        f"apps[name={app_name}].helm.values.resources[{idx}]",
                        kind,
                        name,
                        chunk_max_lines,
                        chunk_overlap_lines,
                        chunk_max_chars=chunk_max_chars,
                    )
                continue

        chunk_id = _append_chunks(
            chunks,
            chunk_id,
            values_str,
            app_name,
            app_namespace,
            chart_name,
            f"apps[name={app_name}].helm.values",
            "HelmValues",
            "values.yaml",
            chunk_max_lines,
            chunk_overlap_lines,
            block_key="values",
            chunk_max_chars=chunk_max_chars,
        )
        chunk_id = _append_block_chunks(
            chunks,
            chunk_id,
            values_str,
            app_name,
            app_namespace,
            chart_name,
            f"apps[name={app_name}].helm.values",
            "HelmValues",
            "values.yaml",
            chunk_max_lines,
            chunk_overlap_lines,
            chunk_max_chars=chunk_max_chars,
        )

    return chunks


def _append_chunks(
    chunks: list[AppChunk],
    chunk_id: int,
    content: str,
    app_name: str,
    app_namespace: str,
    chart_name: str,
    yaml_path: str,
    embedded_kind: str | None,
    embedded_name: str | None,
    chunk_max_lines: int,
    chunk_overlap_lines: int,
    block_key: str | None = None,
    chunk_max_chars: int | None = None,
) -> int:
    for chunk in chunk_text(content, chunk_max_lines, chunk_overlap_lines, chunk_max_chars):
        chunks.append(
            AppChunk(
                text=chunk.text,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                chunk_id=chunk_id,
                app_name=app_name,
                app_namespace=app_namespace,
                chart_name=chart_name,
                yaml_path=yaml_path,
                embedded_kind=embedded_kind,
                embedded_name=embedded_name,
                block_key=block_key,
            )
        )
        chunk_id += 1
    return chunk_id


def _append_block_chunks(
    chunks: list[AppChunk],
    chunk_id: int,
    content: str,
    app_name: str,
    app_namespace: str,
    chart_name: str,
    yaml_path: str,
    embedded_kind: str | None,
    embedded_name: str | None,
    chunk_max_lines: int,
    chunk_overlap_lines: int,
    skip_keys: set[str] | None = None,
    chunk_max_chars: int | None = None,
) -> int:
    blocks = extract_yaml_block_scalars(content)
    if not blocks:
        return chunk_id

    for block in blocks:
        if skip_keys and block.key in skip_keys:
            continue
        block_path = f"{yaml_path}.block[key={block.key}]"
        for chunk in chunk_text(block.text, chunk_max_lines, chunk_overlap_lines, chunk_max_chars):
            chunks.append(
                AppChunk(
                    text=chunk.text,
                    start_line=block.start_line + chunk.start_line - 1,
                    end_line=block.start_line + chunk.end_line - 1,
                    chunk_id=chunk_id,
                    app_name=app_name,
                    app_namespace=app_namespace,
                    chart_name=chart_name,
                    yaml_path=block_path,
                    embedded_kind=embedded_kind,
                    embedded_name=embedded_name,
                    block_key=block.key,
                )
            )
            chunk_id += 1
    return chunk_id


def _resolve_chart_name(source: dict[str, Any]) -> str:
    chart = source.get("chart") if isinstance(source, dict) else None
    if chart:
        return str(chart)
    if isinstance(source, dict):
        if "kustomize" in source:
            return "kustomize"
        if "path" in source:
            return "kustomize"
    return ""


def _safe_load_yaml(text: str) -> Any:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False)
