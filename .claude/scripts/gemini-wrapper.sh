#!/usr/bin/env bash
# Gemini CLI wrapper for Claude Code integration
# Requires: GOOGLE_API_KEY environment variable
set -euo pipefail

MODEL="${GEMINI_MODEL:-gemini-3-flash}"
QUERY="${1:-}"

if [[ -z "$QUERY" ]]; then
  echo "Usage: gemini-wrapper.sh <query> [model]"
  echo ""
  echo "Models: gemini-3-flash (default), gemini-3-pro, gemini-2.5-pro, gemini-2.5-flash"
  echo ""
  echo "Set GOOGLE_API_KEY environment variable first."
  exit 1
fi

if [[ -n "${2:-}" ]]; then
  MODEL="$2"
fi

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  # Fallback to gemini CLI if GOOGLE_API_KEY not set
  if command -v gemini &> /dev/null; then
    echo "Using gemini CLI (GOOGLE_API_KEY not set)" >&2
    # gemini CLI uses different model naming, so omit --model flag
    gemini "$QUERY"
    exit 0
  else
    echo "Error: GOOGLE_API_KEY not set and gemini CLI not found"
    exit 1
  fi
fi

python3 << EOF
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("$MODEL")

query = '''$QUERY'''
response = model.generate_content(query)
print(response.text)
EOF
