from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import requests

from code_embedder.config import Config


@dataclass
class QdrantClient:
    base_url: str
    api_key: str | None
    timeout: int

    @classmethod
    def from_config(cls, config: Config) -> "QdrantClient":
        return cls(config.qdrant_url, config.qdrant_api_key, config.qdrant_timeout)

    def get_collection(self, name: str) -> dict | None:
        response = self._request("GET", f"/collections/{name}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def create_collection(self, name: str, vector_size: int, distance: str) -> None:
        payload = {"vectors": {"size": vector_size, "distance": distance}}
        response = self._request("PUT", f"/collections/{name}", json=payload)
        response.raise_for_status()

    def create_payload_index(self, name: str, field_name: str, field_schema: str) -> None:
        payload = {"field_name": field_name, "field_schema": field_schema}
        response = self._request("PUT", f"/collections/{name}/index", json=payload)
        if response.status_code == 409:
            return
        response.raise_for_status()

    def upsert_points(self, name: str, points: list[dict]) -> None:
        response = self._request(
            "PUT",
            f"/collections/{name}/points",
            params={"wait": "true"},
            json={"points": points},
        )
        response.raise_for_status()

    def delete_by_paths(self, name: str, repo: str, paths: Iterable[str]) -> None:
        for path in paths:
            payload = {
                "filter": {
                    "must": [
                        {"key": "repo", "match": {"value": repo}},
                        {"key": "path", "match": {"value": path}},
                    ]
                }
            }
            response = self._request(
                "POST",
                f"/collections/{name}/points/delete",
                params={"wait": "true"},
                json=payload,
            )
            response.raise_for_status()

    def search_dense(
        self,
        name: str,
        vector: list[float],
        limit: int,
        repo: str | None = None,
    ) -> list[dict]:
        payload: dict[str, object] = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }
        if repo:
            payload["filter"] = {
                "must": [{"key": "repo", "match": {"value": repo}}],
            }
        response = self._request(
            "POST",
            f"/collections/{name}/points/search",
            json=payload,
        )
        response.raise_for_status()
        return response.json().get("result", [])

    def search_text(
        self,
        name: str,
        query: str,
        limit: int,
        repo: str | None = None,
    ) -> list[dict]:
        payload: dict[str, object] = {
            "query": query,
            "limit": limit,
            "with_payload": True,
        }
        if repo:
            payload["filter"] = {
                "must": [{"key": "repo", "match": {"value": repo}}],
            }
        response = self._request(
            "POST",
            f"/collections/{name}/points/search",
            json=payload,
        )
        response.raise_for_status()
        return response.json().get("result", [])

    def _request(self, method: str, path: str, **kwargs: object) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        extra_headers = kwargs.pop("headers", None)
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)
        return requests.request(method, url, headers=headers, timeout=self.timeout, **kwargs)


def ensure_collection(
    client: QdrantClient,
    config: Config,
    vector_size: int,
) -> None:
    if config.vector_size is not None and config.vector_size != vector_size:
        raise ValueError(
            "Configured vector size does not match embeddings: "
            f"{config.vector_size} != {vector_size}."
        )

    collection = client.get_collection(config.qdrant_collection)
    created = False
    if collection is None:
        size = config.vector_size or vector_size
        client.create_collection(config.qdrant_collection, size, config.vector_distance)
        created = True
    else:
        actual = (
            collection.get("result", {})
            .get("config", {})
            .get("params", {})
            .get("vectors", {})
            .get("size")
        )

        if actual and int(actual) != vector_size:
            raise ValueError(
                f"Collection vector size mismatch: {actual} != {vector_size}."
            )

    if config.store_text and config.create_text_index:
        if created:
            client.create_payload_index(config.qdrant_collection, config.text_field, "text")
            return

        payload_schema = collection.get("result", {}).get("payload_schema", {})
        if config.text_field not in payload_schema:
            client.create_payload_index(config.qdrant_collection, config.text_field, "text")
