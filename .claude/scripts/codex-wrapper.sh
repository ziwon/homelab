#!/usr/bin/env bash
# Codex CLI wrapper for Claude Code integration
set -euo pipefail

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  review)
    # Code review: reads from stdin or file
    if [[ -n "${1:-}" && -f "$1" ]]; then
      codex review < "$1"
    else
      codex review
    fi
    ;;
  exec)
    # Execute task non-interactively
    codex exec "$@"
    ;;
  chat)
    # Interactive chat (for testing)
    codex "$@"
    ;;
  mcp)
    # Run as MCP server
    codex mcp-server
    ;;
  *)
    echo "Usage: codex-wrapper.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  review [file]  - Review code from stdin or file"
    echo "  exec <prompt>  - Execute coding task"
    echo "  chat           - Interactive mode"
    echo "  mcp            - Run as MCP server"
    ;;
esac
