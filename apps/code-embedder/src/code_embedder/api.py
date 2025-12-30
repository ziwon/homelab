from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from code_embedder.config import Config
from code_embedder.main import run_index
from code_embedder.prompt import render_prompt
from code_embedder.qdrant import QdrantClient
from code_embedder.search import hybrid_search

app = FastAPI(title="code-embedder")


class IngestRequest(BaseModel):
    full_reindex: bool | None = None
    commit_sha: str | None = None
    git_base_ref: str | None = None
    git_head_ref: str | None = None
    repo_path: str | None = None
    repo_name: str | None = None


class IngestResponse(BaseModel):
    commit: str
    files_indexed: int
    files_deleted: int
    chunks_indexed: int
    bytes_indexed: int


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(10, ge=1, le=100)
    use_dense: bool = True
    use_bm25: bool = True
    rrf_k: int = Field(60, ge=1, le=200)
    return_prompt: bool = True
    issue_description: str | None = None


class SearchHitResponse(BaseModel):
    id: str
    score: float
    payload: dict[str, Any]


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    prompt: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    config = _apply_overrides(Config.load(), request)
    stats = run_index(config)
    return IngestResponse(
        commit=stats.commit,
        files_indexed=stats.files_indexed,
        files_deleted=stats.files_deleted,
        chunks_indexed=stats.chunks_indexed,
        bytes_indexed=stats.bytes_indexed,
    )


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    if not request.use_dense and not request.use_bm25:
        raise HTTPException(status_code=400, detail="At least one of use_dense or use_bm25 must be true")

    config = Config.load()
    client = QdrantClient.from_config(config)

    try:
        hits = hybrid_search(
            client=client,
            config=config,
            query=request.query,
            limit=request.limit,
            use_dense=request.use_dense,
            use_bm25=request.use_bm25,
            rrf_k=request.rrf_k,
            repo=config.repo_name,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt = None
    if request.return_prompt:
        if not config.store_text:
            raise HTTPException(status_code=400, detail="STORE_TEXT must be true for prompt output")
        if not request.issue_description:
            raise HTTPException(status_code=400, detail="issue_description is required when return_prompt=true")
        prompt = render_prompt(config, hits, request.issue_description)

    return SearchResponse(
        hits=[SearchHitResponse(id=hit.id, score=hit.score, payload=hit.payload) for hit in hits],
        prompt=prompt,
    )


def _apply_overrides(config: Config, request: IngestRequest) -> Config:
    overrides: dict[str, Any] = {}
    if request.full_reindex is not None:
        overrides["full_reindex"] = request.full_reindex
    if request.commit_sha:
        overrides["commit_sha"] = request.commit_sha
    if request.git_base_ref:
        overrides["git_base_ref"] = request.git_base_ref
    if request.git_head_ref:
        overrides["git_head_ref"] = request.git_head_ref
    if request.repo_path:
        overrides["repo_path"] = Path(request.repo_path).resolve()
    if request.repo_name:
        overrides["repo_name"] = request.repo_name

    if overrides:
        return replace(config, **overrides)
    return config


def run() -> None:
    import os
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8090"))
    log_level = os.getenv("API_LOG_LEVEL", "info")

    uvicorn.run(app, host=host, port=port, log_level=log_level)
