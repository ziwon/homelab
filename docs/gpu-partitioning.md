# NVIDIA MPS + Ray Hybrid Resource Partitioning Architecture

## Overview

This document describes a hybrid CPU/GPU resource partitioning architecture using NVIDIA MPS (Multi-Process Service) for GPU sharing and Ray for distributed task scheduling on Intel’s hybrid core architecture.

### Hardware Specifications

|Component|Specification                                               |
|---------|------------------------------------------------------------|
|CPU      |Intel Core Ultra 9 285K (8P + 16E + 14LP-E cores @ 5.70 GHz)|
|GPU      |NVIDIA GeForce RTX 5080 (16GB VRAM)                         |
|RAM      |128GB DDR5-5600                                             |
|Storage  |NVMe (XFS) for /data and /cache                             |

-----

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Host: Intel Core Ultra 9 285K                            │
│                        RAM: 128GB DDR5 | GPU: RTX 5080 16GB                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Docker Environment                               │   │
│  │                                                                          │   │
│  │  ┌────────────────────┐    ┌──────────────────────────────────────────┐  │   │
│  │  │   nvidia-mps       │    │              ray-node                    │  │   │
│  │  │   Container        │    │              Container                   │  │   │
│  │  │                    │    │                                          │  │   │
│  │  │  ┌──────────────┐  │    │  ┌─────────────────────────────────────┐ │  │   │
│  │  │  │ MPS Control  │  │    │  │           Ray Cluster               │ │  │   │
│  │  │  │   Daemon     │◄─┼────┼──┤                                     │ │  │   │
│  │  │  └──────────────┘  │    │  │  ┌─────────┐     ┌───────────────┐  │ │  │   │
│  │  │         │          │    │  │  │Ray Head │     │  Ray Worker   │  │ │  │   │
│  │  │         ▼          │    │  │  │(E-cores)│     │  (P-cores)    │  │ │  │   │
│  │  │  ┌──────────────┐  │    │  │  │         │     │               │  │ │  │   │
│  │  │  │ /mps/pipe    │◄─┼────┼──┤  │ CPU_E:16│     │ CPU_P: 8      │  │ │  │   │
│  │  │  │ (Unix Socket)│  │    │  │  │ num_cpu:0     │ num_gpus: 16  │  │ │  │   │
│  │  │  └──────────────┘  │    │  │  └─────────┘     │ VRAM_GB: 16   │  │ │  │   │
│  │  │                    │    │  │                  └───────────────┘  │ │  │   │
│  │  └────────────────────┘    │  └─────────────────────────────────────┘ │  │   │
│  │                            └──────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
``````
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Host: Intel Core Ultra 9 285K                            │
│                        RAM: 128GB DDR5 | GPU: RTX 5080 16GB                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         Docker Environment                               │   │
│  │                                                                          │   │
│  │  ┌────────────────────┐    ┌──────────────────────────────────────────┐  │   │
│  │  │   nvidia-mps       │    │              ray-node                    │  │   │
│  │  │   Container        │    │              Container                   │  │   │
│  │  │                    │    │                                          │  │   │
│  │  │  ┌──────────────┐  │    │  ┌─────────────────────────────────────┐ │  │   │
│  │  │  │ MPS Control  │  │    │  │           Ray Cluster               │ │  │   │
│  │  │  │   Daemon     │◄┼────┼──┤                                     │ │  │   │
│  │  │  └──────────────┘  │    │  │  ┌─────────┐     ┌───────────────┐  │ │  │   │
│  │  │         │          │    │  │  │Ray Head │     │  Ray Worker   │  │ │  │   │
│  │  │        ▼          │    │  │  │(E-cores)│     │  (P-cores)    │  │ │  │   │
│  │  │  ┌──────────────┐  │    │  │  │         │     │               │  │ │  │   │
│  │  │  │ /mps/pipe    │◄┼────┼──┤  │ CPU_E:16│     │ CPU_P: 8      │  │ │  │   │
│  │  │  │ (Unix Socket)│  │    │  │  │ num_cpu:0     │ num_gpus: 16  │  │ │  │   │
│  │  │  └──────────────┘  │    │  │  └─────────┘     │ VRAM_GB: 16   │  │ │  │   │
│  │  │                    │    │  │                  └───────────────┘  │ │  │   │
│  │  └────────────────────┘    │  └─────────────────────────────────────┘ │  │   │
│  │                            └──────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

-----

## CPU Core Allocation

Intel Core Ultra 9 285K features a hybrid architecture with three types of cores:

```
Intel Core Ultra 9 285K - Hybrid Architecture
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Physical Cores                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  P-Cores (Performance)              E-Cores (Efficient)                     │
│  ┌─────────────────────┐            ┌─────────────────────────────────────┐ │
│  │ Cores 0-7 (8 cores) │            │ Cores 8-23 (16 cores)               │ │
│  │ @ 5.70 GHz boost    │            │ @ 4.60 GHz boost                    │ │
│  │                     │            │                                     │ │
│  │ ┌─────────────────┐ │            │ ┌─────────────────────────────────┐ │ │
│  │ │   Ray Worker    │ │            │ │         Ray Head                │ │ │
│  │ │                 │ │            │ │                                 │ │ │
│  │ │ • GPU workloads │ │            │ │ • GCS (Global Control Store)    │ │ │
│  │ │ • ML training   │ │            │ │ • Dashboard (port 8265)         │ │ │
│  │ │ • Inference     │ │            │ │ • Object Store                  │ │ │
│  │ │ • HPC tasks     │ │            │ │ • Scheduling                    │ │ │
│  │ └─────────────────┘ │            │ │ • Data preprocessing            │ │ │
│  │                     │            │ └─────────────────────────────────┘ │ │
│  │ taskset -c 0-7      │            │ taskset -c 8-23                     │ │
│  └─────────────────────┘            └─────────────────────────────────────┘ │
│                                                                             │
│  LP-E Cores (Low Power Efficient) - Reserved for OS                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Cores 24-37 (14 cores) - Available for future expansion                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Assignment Strategy

|Core Type |Core IDs|Count|Assignment |Use Case                                |
|----------|--------|-----|-----------|----------------------------------------|
|P-Cores   |0-7     |8    |Ray Worker |GPU tasks, ML training, inference       |
|E-Cores   |8-23    |16   |Ray Head   |Control plane, scheduling, preprocessing|
|LP-E Cores|24-37   |14   |OS/Reserved|System tasks, future expansion          |

-----

## GPU Memory Partitioning with MPS

NVIDIA MPS enables concurrent GPU access from multiple processes, allowing fine-grained VRAM allocation.

```
NVIDIA RTX 5080 - 16GB VRAM with MPS (Multi-Process Service)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Physical GPU                          Logical GPU Resources (Ray)
┌────────────────────────┐            ┌────────────────────────────────────────┐
│                        │            │                                        │
│   RTX 5080 16GB        │    MPS     │   num_gpus=16 (1GB per logical unit)   │
│   ┌────────────────┐   │  ───────► │                                        │
│   │                │   │            │   ┌──┬──┬──┬──┬──┬──┬──┬──┐            │
│   │   16GB VRAM    │   │            │   │1G│1G│1G│1G│1G│1G│1G│1G│  8GB       │
│   │                │   │            │   ├──┼──┼──┼──┼──┼──┼──┼──┤            │
│   │   Shared via   │   │            │   │1G│1G│1G│1G│1G│1G│1G│1G│  8GB       │
│   │   MPS Daemon   │   │            │   └──┴──┴──┴──┴──┴──┴──┴──┘            │
│   │                │   │            │                                        │
│   └────────────────┘   │            │   Total: 16 logical GPU units          │
│                        │            │                                        │
└────────────────────────┘            └────────────────────────────────────────┘
```

### Allocation Examples

#### Example 1: Fine-grained (16 × 1GB tasks)

```
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│T1│T2│T3│T4│T5│T6│T7│T8│T9│10│11│12│13│14│15│16│
└──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
 16 concurrent small inference tasks (1GB each)
```

#### Example 2: 70/30 Split (Training vs Inference)

```
┌───────────────────────────┬───────────┐
│     Training (11GB)       │ Inf (5GB) │
│     num_gpus=11           │ num_gpus=5│
└───────────────────────────┴───────────┘
```

#### Example 3: Mixed Workloads

```
┌───────────┬───────────┬──┬──┬──┬──┐
│  LLM (8G) │ Train(4G) │S1│S2│S3│S4│
│ num_gpus=8│ num_gpus=4│1G│1G│1G│1G│
└───────────┴───────────┴──┴──┴──┴──┘
 S = Small inference tasks (1GB each)
```

-----

## Data Flow Architecture

```
                                    Request Flow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│   Client     │     │     n8n      │     │           Ray Cluster            │
│  (External)  │     │  Workflow    │     │                                  │
└──────┬───────┘     └──────┬───────┘     │  ┌────────────┐ ┌─────────────┐  │
       │                    │             │  │  Ray Head  │ │ Ray Worker  │  │
       │ HTTPS              │ HTTP API    │  │  (E-cores) │ │ (P-cores)   │  │
        ▼                   ▼             │  │            │ │             │  │
┌──────────────┐     ┌──────────────┐     │  │ Scheduler  │ │ GPU Tasks   │  │
│ Cloudflare   │────►│   Webhook    │───► │  │     │      │ │     ▲       │  │
│   Tunnel     │     │   Trigger    │     │  │     ▼      │ │     │       │  │
└──────────────┘     └──────────────┘     │  │ Task Queue │─┼─────┘       │  │
                                          │  └────────────┘ └─────────────┘  │
                                          └──────────────────────────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────────┐
                                          │         MPS Layer                │
                                          │  ┌────────────────────────────┐  │
                                          │  │   Shared GPU Memory Pool   │  │
                                          │  │      (16GB VRAM)           │  │
                                          │  └────────────────────────────┘  │
                                          └──────────────────────────────────┘
``````
                                    Request Flow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│   Client     │     │     n8n      │     │           Ray Cluster            │
│  (External)  │     │  Workflow    │     │                                  │
└──────┬───────┘     └──────┬───────┘     │  ┌────────────┐ ┌─────────────┐  │
       │                    │             │  │  Ray Head  │ │ Ray Worker  │  │
       │ HTTPS              │ HTTP API    │  │  (E-cores) │ │ (P-cores)   │  │
       ▼                   ▼            │  │            │ │             │  │
┌──────────────┐     ┌──────────────┐     │  │ Scheduler  │ │ GPU Tasks   │  │
│ Cloudflare   │────►│   Webhook    │────► │     │      │ │    ▲       │  │
│   Tunnel     │     │   Trigger    │     │  │     ▼     │ │     │       │  │
└──────────────┘     └──────────────┘     │  │ Task Queue │─┼─────┘       │  │
                                          │  └────────────┘ └─────────────┘  │
                                          └──────────────────────────────────┘
                                                         │
                                                         ▼
                                          ┌──────────────────────────────────┐
                                          │         MPS Layer                │
                                          │  ┌────────────────────────────┐  │
                                          │  │   Shared GPU Memory Pool   │  │
                                          │  │      (16GB VRAM)           │  │
                                          │  └────────────────────────────┘  │
                                          └──────────────────────────────────┘
```

-----

## Storage Layout

### Filesystem Comparision: cache vs data

| Category                        | **/cache** | **/data** | Meaning / Notes                                                                                |
| ------------------------------- | --------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------- |
| **Inode size (isize)**          | **1024 bytes**              | **512 bytes**              | Larger inode on `/cache` → better for metadata-heavy workloads (BuildKit layers, small files). |
| **Allocation Groups (agcount)** | 4                           | 4                          | Same count.                                                                                    |
| **AG size (agsize)**            | **6,103,488 blocks**        | **103,227,456 blocks**     | `/data` is massively larger → optimized for large dataset storage.                             |
| **Sector size (sectsz)**        | 512                         | 512                        | Same.                                                                                          |
| **Block size (bsize)**          | 4096                        | 4096                       | Same.                                                                                          |
| **Inode max percent (imaxpct)** | 25%                         | 5%                         | `/cache` allows more inodes → ideal for many small files. `/data` optimized for large files.   |
| **Reflink / rmapbt / finobt**   | Enabled                     | Enabled                    | Same modern XFS features enabled.                                                              |
| **Realtime volume**             | none                        | none                       | Both using standard data volumes.                                                              |

### XFS Volume Configuration
```
# --------------------------------------------------------------------
# XFS cache volume: BuildKit, container layers, Ray temp, small files
# - noatime: avoid needless metadata writes
# - lazytime: batch timestamp updates
# - inode64: full-disk inode placement
# - filestreams: better locality for many small files
# - logbsize=256k: optimize log size for small files to reduce disk I/O
# --------------------------------------------------------------------
LABEL=CACHE                                             /cache      xfs     noatime,lazytime,inode64,filestreams,logbsize=256k                0       2

# --------------------------------------------------------------------
# XFS data volume: large ML datasets, checkpoints, Parquet, etc.
# - noatime: avoid atime updates on read
# - inode64: allow inode allocation across full disk
# - allocsize=256m: preallocate large extents for big sequential writes
# --------------------------------------------------------------------
LABEL=DATA                                              /data       xfs     noatime,inode64,allocsize=256m                      0       2


```

```
Storage Tiers for Ray Workloads
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   /cache (XFS)  │  │   /data (XFS)   │  │   tmpfs (RAM)   │
│                 │  │                 │  │                 │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│                 │  │                 │  │                 │
│ • MPS pipe/log  │  │ • Ray storage   │  │ • Ray temp      │
│ • Ray spill     │  │ • Checkpoints   │  │ • Object store  │
│ • Build cache   │  │ • Model weights │  │ • Plasma        │
│                 │  │ • Datasets      │  │                 │
│ Low-latency I/O │  │ Persistent data │  │ Ultra-fast I/O  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Container Mount Points

|Container Path|Host Path               |Purpose           |
|--------------|------------------------|------------------|
|`/mps/pipe`   |`/cache/nvidia-mps/pipe`|MPS Unix socket   |
|`/mps/log`    |`/cache/nvidia-mps/log` |MPS daemon logs   |
|`/tmp/ray`    |`tmpfs (32GB)`          |Ray session data  |
|`/ray/storage`|`/data/ray/storage`     |Persistent storage|

-----

## Docker Compose Configuration

### docker-compose.yml

```yaml
services:
  nvidia-mps:
    image: nvidia/cuda:12.9.1-base-ubuntu24.04
    container_name: nvidia-mps
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_MPS_PIPE_DIRECTORY=/mps/pipe
      - CUDA_MPS_LOG_DIRECTORY=/mps/log
    volumes:
      - /cache/nvidia-mps/pipe:/mps/pipe
      - /cache/nvidia-mps/log:/mps/log
    command: >
      bash -c "
        nvidia-cuda-mps-control -d &&
        echo 'MPS daemon started' &&
        tail -f /dev/null
      "
    restart: always
    healthcheck:
      test: ["CMD", "test", "-e", "/mps/pipe/control"]
      interval: 5s
      timeout: 3s
      retries: 10
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  ray-node:
    image: rayproject/ray:2.44.0-py310-gpu
    container_name: ray-node
    hostname: ray-node
    restart: always
    runtime: nvidia
    depends_on:
      nvidia-mps:
        condition: service_healthy
    shm_size: "32gb"
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - CUDA_MPS_PIPE_DIRECTORY=/mps/pipe
      - CUDA_MPS_LOG_DIRECTORY=/mps/log
    volumes:
      - ./entrypoint.sh:/usr/local/bin/entrypoint.sh:ro
      - /cache/nvidia-mps/pipe:/mps/pipe
      - /cache/nvidia-mps/log:/mps/log
      - /data/ray/storage:/ray/storage
    tmpfs:
      - /tmp/ray:size=32g,mode=1777
    entrypoint: ["bash", "/usr/local/bin/entrypoint.sh"]
    ports:
      - "8265:8265"   # Dashboard
      - "6379:6379"   # Redis
      - "10001:10001" # Client
```

### entrypoint.sh

```bash
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

echo "[ENTRYPOINT] Starting Ray Head on E-Cores (8-23)..."

taskset -c 8-23 \
ray start --head \
  --node-ip-address=0.0.0.0 \
  --port=${RAY_PORT} \
  --dashboard-host=0.0.0.0 \
  --dashboard-port=8265 \
  --num-cpus=0 \
  --resources='{"CPU_E": 16, "control_plane": 1}' \
  --include-dashboard=true \
  &> ${LOG_DIR}/ray-head.log &

HEAD_PID=$!

echo "[ENTRYPOINT] Waiting for Ray Head..."
sleep 5

if ! ray status --address=${RAY_ADDR} &>/dev/null; then
  echo "[ENTRYPOINT] ERROR: Ray Head failed to start"
  cat ${LOG_DIR}/ray-head.log
  exit 1
fi

echo "[ENTRYPOINT] Starting Ray Worker on P-Cores (0-7)..."

taskset -c 0-7 \
ray start \
  --address=${RAY_ADDR} \
  --num-cpus=8 \
  --num-gpus=16 \
  --resources='{"CPU_P": 8, "RTX5080": 1, "VRAM_GB": 16}' \
  &> ${LOG_DIR}/ray-worker-gpu.log &

WORKER_PID=$!

sleep 3

echo "[ENTRYPOINT] Ray Cluster Status:"
ray status --address=${RAY_ADDR}

echo "============================================"
echo "[ENTRYPOINT] Ray Cluster Ready"
echo "  Dashboard: http://localhost:8265"
echo "  Client:    ray://localhost:10001"
echo "============================================"

tail -F ${LOG_DIR}/ray-head.log ${LOG_DIR}/ray-worker-gpu.log &

wait $HEAD_PID $WORKER_PID
```

-----

## Ray Resource Declaration

### Cluster Resources Summary

|Resource       |Value|Location                    |
|---------------|-----|----------------------------|
|`CPU_E`        |16   |Ray Head (E-cores)          |
|`CPU_P`        |8    |Ray Worker (P-cores)        |
|`num_gpus`     |16   |Logical GPU units (1GB each)|
|`VRAM_GB`      |16   |Total GPU memory            |
|`RTX5080`      |1    |Physical GPU identifier     |
|`control_plane`|1    |Head node marker            |

### Usage Examples

```python
import ray

ray.init("ray://localhost:10001")

# Small inference task (1GB VRAM)
@ray.remote(num_gpus=1)
def small_inference(x):
    import torch
    model = load_small_model()  # ~800MB
    return model(torch.tensor(x).cuda())

# Large training task (8GB VRAM + 4 P-cores)
@ray.remote(num_gpus=8, resources={"CPU_P": 4})
def large_training(data):
    import torch
    model = LargeModel().cuda()  # ~7GB
    # Training logic
    return checkpoint

# CPU-only preprocessing (E-cores)
@ray.remote(resources={"CPU_E": 4})
def data_preprocessing(data):
    # CPU-intensive preprocessing
    return processed_data

# Concurrent execution
futures = [
    small_inference.remote(x1),  # 1GB
    small_inference.remote(x2),  # 1GB
    large_training.remote(data), # 8GB
    data_preprocessing.remote(raw_data),  # E-cores only
]
results = ray.get(futures)
```

-----

## Network Architecture

```
Network Connectivity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    Internet
                        │
                        ▼
            ┌───────────────────────┐
            │   Cloudflare Tunnel   │  ◄── App-level (n8n, etc.)
            │   (per-application)   │
            └───────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Homelab Network                                │
│                                                                             │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│   │   Tailscale     │    │   K3s Cluster   │    │   Docker Host   │         │
│   │ 100.64.0.0/10   │◄──►│   (Kubernetes)  │◄──►│   (Ray + MPS)   │         │
│   │ (Infra-level)   │    │                 │    │                 │         │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│   Note: Cloudflare WARP also uses 100.64.0.0/10 CGNAT range.                │
│         We use Cloudflared tunnels (not WARP) to avoid IP conflicts.        │
└─────────────────────────────────────────────────────────────────────────────┘
```

-----

## References

- [NVIDIA MPS Documentation](https://docs.nvidia.com/deploy/mps/index.html)
- [Ray Documentation](https://docs.ray.io/)
- [Intel Core Ultra 9 285K Specifications](https://ark.intel.com/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [XFS Documentation](https://docs.kernel.org/filesystems/xfs.html)
- [How to Scale Your Model](https://jax-ml.github.io/scaling-book/)
