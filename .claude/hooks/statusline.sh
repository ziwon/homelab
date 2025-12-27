#!/usr/bin/env bash
# Custom status line for Claude Code CLI
# Shows: model, session duration, project info, git changes, k8s/gpu status

# Read JSON input from stdin (provided by Claude Code)
INPUT=$(cat)

# ─────────────────────────────────────────────────────────────
# Session Duration (project-specific)
# ─────────────────────────────────────────────────────────────
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
SESSION_ID=$(echo "$PROJECT_DIR" | md5sum | cut -c1-8)
SESSION_FILE="/tmp/claude-session-${SESSION_ID}"

if [[ ! -f "$SESSION_FILE" ]]; then
  date +%s > "$SESSION_FILE"
fi

START_TIME=$(cat "$SESSION_FILE" 2>/dev/null || date +%s)
NOW=$(date +%s)
DURATION=$((NOW - START_TIME))

if [[ $DURATION -lt 60 ]]; then
  TIME_STR="${DURATION}s"
elif [[ $DURATION -lt 3600 ]]; then
  TIME_STR="$((DURATION / 60))m"
else
  TIME_STR="$((DURATION / 3600))h$((DURATION % 3600 / 60))m"
fi

# ─────────────────────────────────────────────────────────────
# Model (extracted from JSON input - always up-to-date)
# ─────────────────────────────────────────────────────────────
MODEL_DISPLAY=$(echo "$INPUT" | jq -r '.model.display_name // "Unknown"')

# ─────────────────────────────────────────────────────────────
# Git Info
# ─────────────────────────────────────────────────────────────
BRANCH=$(git branch --show-current 2>/dev/null || echo "-")

# Count uncommitted changes (staged + unstaged + untracked)
GIT_CHANGES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [[ "$GIT_CHANGES" -gt 0 ]]; then
  GIT_STATUS="*${GIT_CHANGES}"
else
  GIT_STATUS="✓"
fi

# ─────────────────────────────────────────────────────────────
# K8s Context (cached for performance)
# ─────────────────────────────────────────────────────────────
K8S_CACHE="/tmp/claude-k8s-status"
K8S_CACHE_AGE=60  # refresh every 60 seconds

# Use KUBECONFIG from env or fallback to default
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config.home}"

if [[ -f "$K8S_CACHE" ]]; then
  CACHE_TIME=$(stat -c %Y "$K8S_CACHE" 2>/dev/null || stat -f %m "$K8S_CACHE" 2>/dev/null || echo 0)
  if [[ $((NOW - CACHE_TIME)) -lt $K8S_CACHE_AGE ]]; then
    K8S_INFO=$(cat "$K8S_CACHE")
  fi
fi

if [[ -z "$K8S_INFO" ]]; then
  if command -v kubectl &>/dev/null && [[ -f "$KUBECONFIG" ]]; then
    # Get current context name (short)
    K8S_CTX=$(kubectl config current-context 2>/dev/null)
    if [[ -n "$K8S_CTX" ]]; then
      K8S_CTX=$(echo "$K8S_CTX" | sed 's/.*@//' | cut -c1-8)
      # Quick node check
      NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | /bin/grep -c " Ready" || echo "0")
      K8S_INFO="${K8S_CTX}:${NODE_COUNT}n"
    else
      K8S_INFO="disconn"
    fi
  else
    K8S_INFO="-"
  fi
  echo "$K8S_INFO" > "$K8S_CACHE"
fi

# ─────────────────────────────────────────────────────────────
# System Resources (CPU/RAM) - cached for performance
# ─────────────────────────────────────────────────────────────
SYS_CACHE="/tmp/claude-sys-status"
SYS_CACHE_AGE=10  # refresh every 10 seconds

if [[ -f "$SYS_CACHE" ]]; then
  CACHE_TIME=$(stat -c %Y "$SYS_CACHE" 2>/dev/null || stat -f %m "$SYS_CACHE" 2>/dev/null || echo 0)
  if [[ $((NOW - CACHE_TIME)) -lt $SYS_CACHE_AGE ]]; then
    SYS_INFO=$(cat "$SYS_CACHE")
  fi
fi

if [[ -z "$SYS_INFO" ]]; then
  # CPU utilization (1-minute load average / number of cores)
  if [[ -f /proc/loadavg ]]; then
    LOAD=$(awk '{print $1}' /proc/loadavg)
    CORES=$(nproc 2>/dev/null || echo 1)
    CPU_PCT=$(awk -v load="$LOAD" -v cores="$CORES" 'BEGIN {printf "%.0f", (load/cores)*100}')
  else
    # macOS fallback
    CPU_PCT=$(top -l 1 -n 0 2>/dev/null | awk '/CPU usage/ {print int($3)}' || echo "?")
  fi

  # RAM usage
  if [[ -f /proc/meminfo ]]; then
    MEM_TOTAL=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
    MEM_AVAIL=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    MEM_USED=$((MEM_TOTAL - MEM_AVAIL))
    MEM_PCT=$(awk -v used="$MEM_USED" -v total="$MEM_TOTAL" 'BEGIN {printf "%.0f", (used/total)*100}')
    MEM_TOTAL_GB=$(awk -v total="$MEM_TOTAL" 'BEGIN {printf "%.0f", total/1024/1024}')
    MEM_USED_GB=$(awk -v used="$MEM_USED" 'BEGIN {printf "%.0f", used/1024/1024}')
  else
    # macOS fallback
    MEM_INFO=$(vm_stat 2>/dev/null | awk '/Pages (free|active|inactive|speculative|wired)/ {sum+=$NF} END {print sum}')
    MEM_PCT="?"
    MEM_USED_GB="?"
    MEM_TOTAL_GB="?"
  fi

  SYS_INFO="${CPU_PCT}%|${MEM_USED_GB}/${MEM_TOTAL_GB}G"
  echo "$SYS_INFO" > "$SYS_CACHE"
fi

# ─────────────────────────────────────────────────────────────
# GPU Status (cached for performance)
# ─────────────────────────────────────────────────────────────
GPU_CACHE="/tmp/claude-gpu-status"
GPU_CACHE_AGE=30  # refresh every 30 seconds

if [[ -f "$GPU_CACHE" ]]; then
  CACHE_TIME=$(stat -c %Y "$GPU_CACHE" 2>/dev/null || stat -f %m "$GPU_CACHE" 2>/dev/null || echo 0)
  if [[ $((NOW - CACHE_TIME)) -lt $GPU_CACHE_AGE ]]; then
    GPU_INFO=$(cat "$GPU_CACHE")
  fi
fi

if [[ -z "$GPU_INFO" ]]; then
  if command -v nvidia-smi &>/dev/null; then
    # Get GPU utilization and memory
    GPU_UTIL=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
    GPU_MEM=$(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | awk -F', ' '{printf "%.0f", ($1/$2)*100}')

    if [[ -n "$GPU_UTIL" ]]; then
      GPU_INFO="${GPU_UTIL}%/${GPU_MEM}%"
    else
      GPU_INFO="-"
    fi
  else
    GPU_INFO="-"
  fi
  echo "$GPU_INFO" > "$GPU_CACHE"
fi

# ─────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────
# Format: ⏱ 5m │ 🤖 Sonnet │ 📁 main *3 │ ☸ home:1n │ 💻 25%|32/128G │ 🎮 45%/60%

OUTPUT="⏱ ${TIME_STR}"
OUTPUT+=" │ 🤖 ${MODEL_DISPLAY}"
OUTPUT+=" │ 📁 ${BRANCH} ${GIT_STATUS}"
OUTPUT+=" │ ☸ ${K8S_INFO}"
OUTPUT+=" │ 💻 ${SYS_INFO}"

if [[ "$GPU_INFO" != "-" ]]; then
  OUTPUT+=" │ 🎮 ${GPU_INFO}"
fi

echo -n "$OUTPUT"
