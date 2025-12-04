#!/usr/bin/env bash
set -euo pipefail

RAY_PORT=6379
RAY_ADDR="127.0.0.1:${RAY_PORT}"

mkdir -p /tmp/ray-logs
touch /tmp/ray-logs/ray-head.log
touch /tmp/ray-logs/ray-worker-p.log

echo "[ENTRYPOINT] Starting Ray Head on E-Cores (8-23)..."

# ---------------------------------------------------------
# 1) Ray Head (E-Core, control plane + CPU_E 리소스)
#    - GCS, Dashboard, Object Store
# ---------------------------------------------------------
taskset -c 8-23 \
ray start --head \
  --node-ip-address=127.0.0.1 \
  --port=${RAY_PORT} \
  --dashboard-host=0.0.0.0 \
  --dashboard-port=8265 \
  --num-cpus=16 \
  --resources='{"CPU_E": 16, "control_plane": 1}' \
  --block &> /tmp/ray-logs/ray-head.log &

sleep 5

echo "[ENTRYPOINT] Starting Ray Worker on P-Cores (0-7)..."

# ---------------------------------------------------------
# 2) Ray Worker (P-Core, RL/LLM + GPU)
#    - 논리 리소스: CPU_P, RTX5080, accelerator
# ---------------------------------------------------------
taskset -c 0-7 \
ray start \
  --address=${RAY_ADDR} \
  --num-cpus=8 \
  --num-gpus=1 \
  --resources='{"CPU_P": 8, "RTX5080": 1, "accelerator": 1}' \
  --block &> /tmp/ray-logs/ray-worker-p.log &

echo "[ENTRYPOINT] Ray Head + Worker started."
echo "[ENTRYPOINT] Logs in /tmp/ray-logs"

tail -F /tmp/ray-logs/ray-head.log
