#!/usr/bin/env bash
# Save Claude Code session transcript to cloud storage
# Called by Stop hook when session ends

set -euo pipefail

# Configuration
CLOUD_DIR="${CLAUDE_SESSION_DIR:-$HOME/Dropbox/claude-sessions}"
PROJECT_NAME="homelab"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SESSION_FILE="${CLOUD_DIR}/${PROJECT_NAME}/${TIMESTAMP}.md"

# Create directory if not exists
mkdir -p "$(dirname "$SESSION_FILE")"

# Read session data from stdin (provided by Claude Code)
SESSION_DATA=$(cat)

# Generate session markdown
cat > "$SESSION_FILE" << EOF
# Claude Code Session - ${PROJECT_NAME}

**Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Project**: ${PROJECT_NAME}
**Working Directory**: $(pwd)

---

${SESSION_DATA:-No session data available}

---

*Saved automatically by Claude Code Stop hook*
EOF

# Output confirmation (goes to stderr so it doesn't interfere)
echo "Session saved: ${SESSION_FILE}" >&2
