from __future__ import annotations

import subprocess
from pathlib import Path

from code_embedder.config import Config


def get_changed_files(config: Config) -> tuple[set[str], set[str]]:
    base, head = _resolve_refs(config)
    output = _run_git(config.repo_path, ["diff", "--name-status", base, head])

    changed: set[str] = set()
    deleted: set[str] = set()

    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]

        if status.startswith("R") or status.startswith("C"):
            if len(parts) >= 3:
                deleted.add(parts[1])
                changed.add(parts[2])
            continue

        if status == "D":
            deleted.add(parts[1])
            continue

        changed.add(parts[1])

    return changed, deleted


def get_head_commit(repo_path: Path) -> str | None:
    try:
        return _run_git(repo_path, ["rev-parse", "HEAD"]).strip()
    except RuntimeError:
        return None


def _resolve_refs(config: Config) -> tuple[str, str]:
    if config.git_base_ref and config.git_head_ref:
        return config.git_base_ref, config.git_head_ref

    if config.commit_sha:
        return f"{config.commit_sha}~1", config.commit_sha

    return "HEAD~1", "HEAD"


def _run_git(repo_path: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.strip() or exc.stdout.strip()) from exc
    return result.stdout
