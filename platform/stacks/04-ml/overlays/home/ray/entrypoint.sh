#!/usr/bin/env bash
set -euo pipefail

# Wait for MPS control pipe
echo "[ENTRYPOINT] Waiting for MPS..."
timeout=30
while [ ! -e /mps/pipe/control ] && [ $timeout -gt 0 ]; do
  sleep 1
  ((timeout--))
done

if [ ! -e /mps/pipe/control ]; then
  echo "[ENTRYPOINT] ERROR: MPS pipe not found"
  exit 1
fi

echo "[ENTRYPOINT] MPS ready"

RAY_PORT=6379
RAY_ADDR="127.0.0.1:${RAY_PORT}"
LOG_DIR=/tmp/ray-logs

mkdir -p $LOG_DIR
touch $LOG_DIR/ray-head.log
touch $LOG_DIR/ray-worker-p.log

echo "[ENTRYPOINT] Starting Ray Head on E-Cores (8-23)..."

# ---------------------------------------------------------
# 1) Ray Head (E-Core, control plane + CPU_E 리소스)
#    - GCS, Dashboard, Object Store
# ---------------------------------------------------------
taskset -c 8-23 \
ray start --head \
  --node-ip-address=0.0.0.0 \
  --port=${RAY_PORT} \
  --dashboard-host=0.0.0.0 \
  --dashboard-port=8265 \
  --num-cpus=16 \
  --resources='{"CPU_E": 16, "control_plane": 1}' \
  --include-dashboard=true \
  --block &> $LOG_DIR/ray-head.log &

HEAD_PID=$!

echo "[ENTRYPOINT] Waiting for Ray Head..."
sleep 5

if ! ray status --address=${RAY_ADDR} &>/dev/null; then
  echo "[ENTRYPOINT] ERROR: Ray Head failed to start"
  cat ${LOG_DIR}/ray-head.log
  exit 1
fi

echo "[ENTRYPOINT] Starting Ray Worker on P-Cores (0-7)..."

# ---------------------------------------------------------
# 2) Ray Worker (P-Core, RL/LLM + GPU)
#    - 논리 리소스: CPU_P, RTX5080, accelerator
# ---------------------------------------------------------
taskset -c 0-7 \
ray start \
  --address=${RAY_ADDR} \
  --num-cpus=8 \
  --num-gpus=16 \
  --resources='{"CPU_P": 8, "RTX5080": 1, "accelerator": 1, "VRAM_GB": 16}' \
  --node-manager-port=9001 \
  --object-manager-port=9002 \
  --min-worker-port=20000 \
  --max-worker-port=29999 \
  --block &> $LOG_DIR/ray-worker-p.log &

WORKER_PID=$!

sleep 3

echo "[ENTRYPOINT] Ray Cluster Status:"
ray status --address=${RAY_ADDR}

echo "============================================"
echo "[ENTRYPOINT] Ray Cluster Ready"
echo "  Dashboard: http://localhost:8265"
echo "  Client:    ray://localhost:10001"
echo "============================================"
echo "[ENTRYPOINT] Resources:"
echo "  CPU_E: 16 (E-cores, control plane)"
echo "  CPU_P: 8  (P-cores, compute)"
echo "  GPU:   16 (logical, 1GB each via MPS)"
echo "  VRAM:  16GB"
echo "============================================"

# Log Streaming
tail -F ${LOG_DIR}/ray-head.log ${LOG_DIR}/ray-worker-gpu.log &

# Process Monitoring
wait $HEAD_PID $WORKER_PID