from __future__ import annotations

import logging
from typing import Sequence

import requests

from code_embedder.config import Config

logger = logging.getLogger(__name__)


def embed_texts(config: Config, texts: Sequence[str]) -> list[list[float]]:
    if not texts:
        return []

    logger.debug(
        "embedding request: url=%s items=%s model=%s timeout=%s",
        config.embed_api_url,
        len(texts),
        config.embed_model or "-",
        config.embed_timeout,
    )

    payload: dict[str, object] = {"input": list(texts)}
    if config.embed_model:
        payload["model"] = config.embed_model

    headers = {"Content-Type": "application/json"}
    if config.embed_api_key:
        headers["Authorization"] = f"Bearer {config.embed_api_key}"

    try:
        response = requests.post(
            config.embed_api_url,
            json=payload,
            headers=headers,
            timeout=config.embed_timeout,
        )
    except requests.RequestException:
        logger.exception("embedding request error: url=%s", config.embed_api_url)
        raise

    if not response.ok:
        body = response.text
        if len(body) > 1000:
            body = f"{body[:1000]}...(truncated)"
        logger.error("embedding response error: status=%s body=%s", response.status_code, body)
    response.raise_for_status()

    data = response.json()
    items = data.get("data")
    if not isinstance(items, list):
        raise ValueError("Embedding response missing data array")

    embeddings: list[list[float] | None] = [None] * len(texts)
    for item in items:
        index = item.get("index", 0)
        embedding = item.get("embedding")
        if embedding is None:
            raise ValueError("Embedding response item missing embedding")
        embeddings[index] = embedding

    if any(value is None for value in embeddings):
        raise ValueError("Embedding response missing expected items")

    return [value for value in embeddings if value is not None]
