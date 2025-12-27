#!/usr/bin/env bash
# Local LLM wrapper for Continue-compatible endpoints
set -euo pipefail

MODEL="${1:-qwen3-coder}"
PROMPT="${2:-}"

# Model configurations from Continue config
declare -A ENDPOINTS=(
  ["qwen3-coder"]="http://localhost:8003"
  ["gpt-oss"]="http://localhost:8004"
)

declare -A MODELS=(
  ["qwen3-coder"]="qwen3-coder"
  ["gpt-oss"]="gpt-oss-20b"
)

if [[ -z "$PROMPT" ]]; then
  echo "Usage: local-llm.sh <model> <prompt>"
  echo ""
  echo "Models:"
  echo "  qwen3-coder - Qwen3-Coder-30B (localhost:8003)"
  echo "  gpt-oss     - GPT-OSS-20B (localhost:8004)"
  exit 1
fi

ENDPOINT="${ENDPOINTS[$MODEL]:-}"
MODEL_NAME="${MODELS[$MODEL]:-}"

if [[ -z "$ENDPOINT" ]]; then
  echo "Error: Unknown model '$MODEL'"
  exit 1
fi

# Create JSON payload
PAYLOAD=$(jq -n \
  --arg model "$MODEL_NAME" \
  --arg prompt "$PROMPT" \
  '{
    model: $model,
    messages: [{role: "user", content: $prompt}],
    max_tokens: 4096,
    temperature: 0.7
  }')

# Call the API
RESPONSE=$(curl -s -X POST "$ENDPOINT/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# Extract and print the response
echo "$RESPONSE" | jq -r '.choices[0].message.content // .error.message // "Error: No response"'
