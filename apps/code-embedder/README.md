# code-embedder

Embeds repository source code into Qdrant using a local embedding server.

## Usage

```bash
export REPO_PATH=/repo/path
export QDRANT_URL=http://qdrant:6333
export QDRANT_COLLECTION=codebase-bge-m3
export LLM_EMBED_URL=http://llama-cpp-embed:8080
export COMMIT_SHA=$(git rev-parse HEAD)
python -m code_embedder
```

## API

```bash
code-embedder-api
```

Example requests:

```bash
curl -X POST http://localhost:8090/ingest -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8090/search -H "Content-Type: application/json" -d '{"query":"auth error","issue_description":"auth error when login","limit":5}'
```

Note: Search is always filtered to the configured REPO_NAME.

Default prompt template path:

```bash
export PROMPT_TEMPLATE_PATH=apps/code-embedder/prompts/issue_context.j2
# container path: /app/prompts/issue_context.j2
```

App-of-Apps prompt template path:

```bash
export PROMPT_TEMPLATE_PATH=apps/code-embedder/prompts/app_of_apps_context.j2
# container path: /app/prompts/app_of_apps_context.j2
```

## Key Environment Variables

- REPO_PATH: Path to the git repository (default: current directory)
- REPO_NAME: Repository name used in payload (default: repo folder name)
- QDRANT_URL: Qdrant base URL
- QDRANT_API_KEY: Qdrant API key (optional)
- QDRANT_COLLECTION: Target collection name
- VECTOR_SIZE: Vector size for collection creation (optional if collection exists)
- VECTOR_DISTANCE: Cosine | Dot | Euclid (default: Cosine)
- LLM_EMBED_URL: Embedding server base URL or full embeddings endpoint
- EMBED_API_URL: Full embeddings endpoint (overrides LLM_EMBED_URL)
- EMBED_API_KEY: Embedding API key (optional)
- EMBED_MODEL: Embedding model name (optional)
- EMBED_TEXT_PREFIX: Prefix for embedding inputs (default: passage: )
- CONTEXT_TEMPLATE: Prefix template (placeholders: repo, path, lang, structure, app_name, app_namespace, chart_name, yaml_path, embedded_kind, embedded_name, block_key, chunk_id, start_line, end_line)
- INCLUDE_STRUCTURE_HINTS: true to include YAML/JSON structure hints (default: true)
- STRUCTURE_MAX_ITEMS: Max structure entries per chunk (default: 16)
- STRUCTURE_MAX_CHARS: Max structure hint characters (default: 800)
- QUERY_TEXT_PREFIX: Prefix for search queries (default: query: )
- PROMPT_TEMPLATE: Jinja template for prompt output
- PROMPT_TEMPLATE_PATH: Path to a Jinja template file (overrides PROMPT_TEMPLATE)
- PROMPT_MAX_CHUNKS: Max chunks rendered in prompt (default: 12)
- EMBED_BATCH_SIZE: Embedding batch size (default: 16)
- QDRANT_BATCH_SIZE: Qdrant upsert batch size (default: 64)
- COMMIT_SHA: Commit SHA for metadata and diff base (optional)
- GIT_BASE_REF: Base ref for diff (optional)
- GIT_HEAD_REF: Head ref for diff (optional)
- FULL_REINDEX: true to index all files
- INCLUDE_EXTENSIONS: Comma-separated extensions to include
- INCLUDE_FILES: Comma-separated filenames to include
- EXCLUDE_DIRS: Comma-separated directory names to skip
- MAX_FILE_BYTES: Max file size in bytes (default: 1000000)
- CHUNK_MAX_LINES: Max lines per chunk (default: 200)
- CHUNK_OVERLAP_LINES: Overlap lines between chunks (default: 20)
- CHUNK_MAX_CHARS: Max characters per chunk (optional, to avoid oversized embedding inputs)
- STORE_TEXT: true to store chunk text for BM25 (default: true)
- TEXT_FIELD: Payload field for stored text (default: text)
- CREATE_TEXT_INDEX: true to create Qdrant text index (default: true)
- ENABLE_DELETE: true to delete removed/changed files before upsert
- DRY_RUN: true to skip Qdrant writes
- API_HOST: FastAPI bind host (default: 0.0.0.0)
- API_PORT: FastAPI bind port (default: 8090)
- API_LOG_LEVEL: FastAPI log level (default: info)

## Prompt Template

Template context:

- `chunks`: list of items with `file_path`, `language`, `structure`, `score`, `code_content`
- `issue_description`: original issue text injected into the prompt
- Optional fields: `class_name`, `function_name` (empty unless you populate them)
- App-of-Apps fields: `app_name`, `app_namespace`, `chart_name`, `yaml_path`, `embedded_kind`, `embedded_name`, `block_key`
- App-of-Apps `block_key`: `values` for Helm/raw values chunks, `kustomize` for kustomize source chunks

## Argo Workflows (Index Trigger)

WorkflowTemplate and RBAC live in `platform/stacks/04-ml/overlays/home/code-embedder.yaml`.

Required GitHub secrets for ARC submit:

- `ARGO_WORKFLOWS_TOKEN`: token for `code-embedder-runner` service account

## Qdrant Collection

Example:

```bash
curl -X PUT "$QDRANT_URL/collections/codebase-bge-m3" \
  -H "Content-Type: application/json" \
  -H "api-key: $QDRANT_API_KEY" \
  -d '{"vectors":{"size":1024,"distance":"Cosine"}}'
```

## Notes

- By default, uses OpenAI-compatible `/v1/embeddings`.
- Set EMBED_API_URL if your server uses a different endpoint.
- For the first run or repos without history, set FULL_REINDEX=true.
- Prompt output requires STORE_TEXT=true.
