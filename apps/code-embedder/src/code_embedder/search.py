from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

from code_embedder.config import Config
from code_embedder.embedder import embed_texts
from code_embedder.qdrant import QdrantClient


@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float
    payload: dict


def hybrid_search(
    *,
    client: QdrantClient,
    config: Config,
    query: str,
    limit: int,
    use_dense: bool,
    use_bm25: bool,
    rrf_k: int,
    repo: str | None,
) -> list[SearchHit]:
    dense_hits: list[SearchHit] = []
    text_hits: list[SearchHit] = []

    if use_dense:
        dense_hits = _search_dense(client, config, query, limit, repo)

    if use_bm25:
        text_hits = _search_text(client, config, query, limit, repo)

    if use_dense and use_bm25:
        return _rrf_merge([dense_hits, text_hits], rrf_k, limit)

    if use_dense:
        return dense_hits[:limit]

    return text_hits[:limit]


def _search_dense(
    client: QdrantClient,
    config: Config,
    query: str,
    limit: int,
    repo: str | None,
) -> list[SearchHit]:
    query_text = f"{config.query_text_prefix}{query}" if config.query_text_prefix else query
    if config.query_max_chars and len(query_text) > config.query_max_chars:
        logging.warning(
            "Truncating query for embedding: len=%s max=%s",
            len(query_text),
            config.query_max_chars,
        )
        query_text = query_text[: config.query_max_chars]
    vector = embed_texts(config, [query_text])[0]
    results = client.search_dense(config.qdrant_collection, vector, limit, repo=repo)
    return _to_hits(results)


def _search_text(
    client: QdrantClient,
    config: Config,
    query: str,
    limit: int,
    repo: str | None,
) -> list[SearchHit]:
    try:
        results = client.search_text(config.qdrant_collection, query, limit, repo=repo)
    except Exception as exc:  # noqa: BLE001
        logging.warning("BM25 search failed: %s", exc)
        return []
    return _to_hits(results)


def _to_hits(results: Iterable[dict]) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for item in results:
        payload = item.get("payload") or {}
        hits.append(
            SearchHit(
                id=str(item.get("id")),
                score=float(item.get("score", 0.0)),
                payload=payload,
            )
        )
    return hits


def _rrf_merge(lists: list[list[SearchHit]], k: int, limit: int) -> list[SearchHit]:
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            score = 1.0 / (k + rank)
            scores[hit.id] = scores.get(hit.id, 0.0) + score
            payloads.setdefault(hit.id, hit.payload)

    sorted_ids = sorted(scores, key=scores.get, reverse=True)[:limit]
    return [SearchHit(id=item_id, score=scores[item_id], payload=payloads[item_id]) for item_id in sorted_ids]
