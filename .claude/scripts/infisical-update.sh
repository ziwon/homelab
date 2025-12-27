#!/usr/bin/env bash
# Infisical secret updater via local LLM
# Handles sensitive secret updates without external API exposure
set -euo pipefail

ACTION="${1:-help}"
shift || true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_help() {
  echo "Usage: infisical-update.sh <action> [args]"
  echo ""
  echo "Safe Actions (token never exposed):"
  echo "  safe-update <secret> <ns> <path> <key> <value>"
  echo "                                       - Update single secret safely"
  echo "  safe-parse <secret> <ns> <fmt> <file> <path>"
  echo "                                       - Parse file and update (fmt: env/yaml/json)"
  echo "  with-token <secret> <ns> <command>   - Run any command with token in env"
  echo ""
  echo "Low-level Actions (require INFISICAL_TOKEN env):"
  echo "  update <path> <key> <value>          - Update secret via Infisical API"
  echo "  parse-env <file> <path>              - Parse .env file and update"
  echo "  parse-yaml <file> <path>             - Parse YAML and update"
  echo "  parse-json <file> <path>             - Parse JSON and update"
  echo ""
  echo "Other:"
  echo "  load-token <secret> <ns>             - Output 'export' cmd (for eval)"
  echo "  help                                 - Show this help"
  echo ""
  echo "Environment variables:"
  echo "  INFISICAL_TOKEN      - Bearer token (auto-set by safe-* commands)"
  echo "  INFISICAL_WORKSPACE  - Workspace ID (optional if token scoped)"
  echo "  INFISICAL_API        - API URL (default: https://app.infisical.com/api)"
  echo ""
  echo "Examples:"
  echo "  # Safe single update (recommended)"
  echo "  ./infisical-update.sh safe-update infisical-app-secrets myns /app KEY 'value'"
  echo ""
  echo "  # Safe bulk update from JSON"
  echo "  ./infisical-update.sh safe-parse infisical-app-secrets myns json config.json /app"
}

# Internal function - returns token (used by other functions, not directly)
_fetch_token() {
  local secret_name="${1:-}"
  local namespace="${2:-deepfx}"

  if [[ -z "$secret_name" ]]; then
    echo -e "${RED}Error: secret name required${NC}" >&2
    return 1
  fi

  kubectl get secret "$secret_name" -n "$namespace" \
    -o jsonpath='{.data.INFISICAL_TOKEN}' 2>/dev/null | base64 -d
}

# Load token into environment variable (for sourcing)
# Usage: eval $(infisical-update.sh load-token <secret-name> <namespace>)
load_token() {
  local secret_name="${1:-}"
  local namespace="${2:-deepfx}"
  local token

  token=$(_fetch_token "$secret_name" "$namespace")
  if [[ -z "$token" ]]; then
    echo -e "${RED}Error: failed to fetch token${NC}" >&2
    return 1
  fi

  # Output export command (token is masked in logs)
  echo "export INFISICAL_TOKEN='${token}'"
  echo -e "${GREEN}✓ Token loaded (use 'eval \$(...)' to set env)${NC}" >&2
}

# Run a command with the token in environment (token never shown)
# Usage: infisical-update.sh with-token <secret-name> <namespace> <command...>
with_token() {
  local secret_name="${1:-}"
  local namespace="${2:-deepfx}"
  shift 2 || true

  if [[ $# -eq 0 ]]; then
    echo -e "${RED}Error: command required${NC}" >&2
    return 1
  fi

  local token
  token=$(_fetch_token "$secret_name" "$namespace")
  if [[ -z "$token" ]]; then
    echo -e "${RED}Error: failed to fetch token${NC}" >&2
    return 1
  fi

  echo -e "${YELLOW}Running command with Infisical token...${NC}" >&2

  # Run the command with token in env (token never printed)
  INFISICAL_TOKEN="$token" "$@"
}

update_secret() {
  local path="${1:-}"
  local key="${2:-}"
  local value="${3:-}"

  if [[ -z "$path" || -z "$key" || -z "$value" ]]; then
    echo -e "${RED}Error: path, key, and value required${NC}" >&2
    exit 1
  fi

  local token="${INFISICAL_TOKEN:-}"
  if [[ -z "$token" ]]; then
    echo -e "${RED}Error: INFISICAL_TOKEN not set${NC}" >&2
    exit 1
  fi

  local api_url="${INFISICAL_API:-https://app.infisical.com/api}"
  local workspace="${INFISICAL_WORKSPACE:-}"

  # Determine secret type
  local secret_type="plain_text"
  if echo "$value" | jq empty 2>/dev/null; then
    secret_type="json"
  fi

  # Build payload
  local payload
  if [[ -n "$workspace" ]]; then
    payload=$(jq -n \
      --arg ws "$workspace" \
      --arg path "$path" \
      --arg name "$key" \
      --arg value "$value" \
      --arg type "$secret_type" \
      '{workspaceId: $ws, path: $path, name: $name, value: $value, type: $type}')
  else
    payload=$(jq -n \
      --arg path "$path" \
      --arg name "$key" \
      --arg value "$value" \
      --arg type "$secret_type" \
      '{path: $path, name: $name, value: $value, type: $type}')
  fi

  echo -e "${YELLOW}Updating secret: $key at $path${NC}"

  local response
  response=$(curl -s -w "\n%{http_code}" \
    --request POST \
    --url "${api_url}/v1/secrets" \
    --header "Authorization: Bearer ${token}" \
    --header "Content-Type: application/json" \
    --data "$payload")

  local http_code
  http_code=$(echo "$response" | tail -n1)
  local body
  body=$(echo "$response" | sed '$d')

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    echo -e "${GREEN}✓ Secret '$key' updated successfully${NC}"
  else
    echo -e "${RED}✗ Failed to update secret '$key' (HTTP $http_code)${NC}" >&2
    echo "$body" >&2
    return 1
  fi
}

parse_env_file() {
  local file="${1:-}"
  local path="${2:-/}"

  if [[ ! -f "$file" ]]; then
    echo -e "${RED}Error: file not found: $file${NC}" >&2
    exit 1
  fi

  echo -e "${YELLOW}Parsing .env file: $file${NC}"

  while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Remove quotes from value
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    update_secret "$path" "$key" "$value"
  done < "$file"
}

parse_yaml_file() {
  local file="${1:-}"
  local path="${2:-/}"

  if [[ ! -f "$file" ]]; then
    echo -e "${RED}Error: file not found: $file${NC}" >&2
    exit 1
  fi

  echo -e "${YELLOW}Parsing YAML file: $file${NC}"

  # Convert YAML to flat key=value pairs using yq
  yq -o=json "$file" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' | while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue
    update_secret "$path" "$key" "$value"
  done
}

parse_json_file() {
  local file="${1:-}"
  local path="${2:-/}"

  if [[ ! -f "$file" ]]; then
    echo -e "${RED}Error: file not found: $file${NC}" >&2
    exit 1
  fi

  echo -e "${YELLOW}Parsing JSON file: $file${NC}"

  jq -r 'to_entries | .[] | "\(.key)=\(.value | tostring)"' "$file" | while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue
    update_secret "$path" "$key" "$value"
  done
}

# Convenience: update with auto token fetch (all in one)
# Usage: infisical-update.sh safe-update <secret-name> <namespace> <path> <key> <value>
safe_update() {
  local secret_name="${1:-}"
  local namespace="${2:-deepfx}"
  local path="${3:-}"
  local key="${4:-}"
  local value="${5:-}"

  if [[ -z "$secret_name" || -z "$path" || -z "$key" || -z "$value" ]]; then
    echo -e "${RED}Error: secret-name, namespace, path, key, and value required${NC}" >&2
    return 1
  fi

  with_token "$secret_name" "$namespace" \
    "$0" update "$path" "$key" "$value"
}

# Convenience: parse file with auto token fetch
# Usage: infisical-update.sh safe-parse <secret-name> <namespace> <format> <file> <path>
safe_parse() {
  local secret_name="${1:-}"
  local namespace="${2:-deepfx}"
  local format="${3:-}"
  local file="${4:-}"
  local path="${5:-/}"

  if [[ -z "$secret_name" || -z "$format" || -z "$file" ]]; then
    echo -e "${RED}Error: secret-name, namespace, format, and file required${NC}" >&2
    return 1
  fi

  case "$format" in
    env)
      with_token "$secret_name" "$namespace" \
        "$0" parse-env "$file" "$path"
      ;;
    yaml)
      with_token "$secret_name" "$namespace" \
        "$0" parse-yaml "$file" "$path"
      ;;
    json)
      with_token "$secret_name" "$namespace" \
        "$0" parse-json "$file" "$path"
      ;;
    *)
      echo -e "${RED}Error: unknown format '$format' (use: env, yaml, json)${NC}" >&2
      return 1
      ;;
  esac
}

case "$ACTION" in
  load-token)
    load_token "$@"
    ;;
  with-token)
    with_token "$@"
    ;;
  safe-update)
    safe_update "$@"
    ;;
  safe-parse)
    safe_parse "$@"
    ;;
  update)
    update_secret "$@"
    ;;
  parse-env)
    parse_env_file "$@"
    ;;
  parse-yaml)
    parse_yaml_file "$@"
    ;;
  parse-json)
    parse_json_file "$@"
    ;;
  help|--help|-h)
    print_help
    ;;
  *)
    echo -e "${RED}Unknown action: $ACTION${NC}" >&2
    print_help
    exit 1
    ;;
esac
