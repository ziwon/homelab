# 🏠 Homelab: AI-Driven Kubernetes Platform

> A Kubernetes-based environment for AI workloads and GitOps automation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![K3s](https://img.shields.io/badge/Kubernetes-K3s-blue?logo=kubernetes)](https://k3s.io/)
[![ArgoCD](https://img.shields.io/badge/GitOps-Argo%20CD-orange?logo=argo)](https://argoproj.github.io/cd/)
[![NVIDIA](https://img.shields.io/badge/GPU-NVIDIA%20RTX%205080-green?logo=nvidia)](https://www.nvidia.com)

---

## Motivation

This project utilizes local hardware (Intel Core Ultra 9, NVIDIA RTX 5080) for AI research and automation. It provides a stable, reproducible Kubernetes environment for various internal services and workloads.

### Cost Efficiency
An AWS [g6.8xlarge](https://instances.vantage.sh/aws/ec2/g6.8xlarge?currency=USD&region=ap-northeast-2) instance costs approximately **$1,780/month** on-demand. This lab offers similar compute and GPU capacity through a one-time hardware investment, providing significant long-term savings.

---

## Hardware

| Component | Specification | Description |
| :--- | :--- | :--- |
| **CPU** | Intel Core Ultra 9 285K | 24 Cores (8P + 16E) |
| **GPU** | NVIDIA GeForce RTX 5080 | 16GB VRAM, 10,752 CUDA Cores |
| **NPU** | Intel AI Boost (Gen 3) | On-chip AI acceleration |
| **RAM** | 128GB DDR5-5600 | Samsung DDR5 |
| **Networking**| Tailscale + Cilium eBPF | Mesh VPN and eBPF-based CNI |

---

## Architecture

The deployment is split into two phases for manageability.

### Phase 1: Bootstrap
Initialization of the base infrastructure using **Helmfile**.
- **Components**: `K3s`, `Cilium`, `Infisical`, `GPU Operator`.
- **Location**: [`/bootstrap`](./bootstrap)

### Phase 2: Platform
Deployment of applications and middle-ware using **Argo CD** (GitOps).
- **Stacks**: Core Infrastructure, Observability, Data, ML/AI, Workloads.
- **Location**: [`/platform`](./platform)

---

## AI Operations (ARC + Claude)

Automation workflows run on self-hosted Kubernetes runners via **Actions Runner Controller (ARC)**.
- **Issue Resolution**: Automated analysis and PR generation for labeled issues.
- **Code Review**: PR analysis for security, performance, and manifest standards.
- **Cluster Integration**: Runners use `kubectl` with gated permissions to verify cluster state.

### LLM Strategy
- **Local (GPT-OSS / Qwen)**: On-premise processing for privacy and basic tasks.
- **Cloud (Claude / Gemini)**: Utilized for complex research and reasoning via secure API integration.

---

## GitOps Infrastructure

Managed through **ArgoCD ApplicationSets** for automated service deployment.
- **Matrix Generator**: Scans repository paths to discover service definitions.
- **Go Templates**: Orchestrates sync waves, dependencies, and resource patches.
- **Infisical**: Integrated secret management without environment exposure.

---

## Resource Partitioning (MPS + Ray)

Optimized resource allocation for AI workloads on hybrid hardware.
- **CPU**: Ray Head pinned to E-cores; Ray Workers pinned to P-cores.
- **GPU**: **NVIDIA MPS** partitions the RTX 5080 into 16 logical units.

> [!NOTE]
> This setup allows 16 concurrent inference tasks with 1GB VRAM allocation each.
> See [GPU Architecture Docs](./docs/gpu-partitioning-architecture.md).

---

## Observability Stack

Instrumentation from eBPF tracing to application telemetry.

![Observability Stack](./docs/observability-stack.svg)

### Monitoring
- **Logs**: Vector → Redpanda → Quickwit
- **Metrics**: VictoriaMetrics (Prometheus-compatible)
- **Traces**: Grafana Tempo
- **Visualization**: Grafana

### Alerting
Anomalies are reported to Slack:
- **Log Monitoring**: **Vector** filters real-time error streams and dispatches notifications.
- **Metric Thresholds**: **VictoriaMetrics (`vmalert`)** evaluates PROMQL rules and triggers alerts via **Alertmanager**.

---

## Developer Guide

### Prerequisites
- [Just](https://github.com/casey/just)
- [Helmfile](https://github.com/helmfile/helmfile)
- [Kubectl](https://kubernetes.io/docs/reference/kubectl/)

### Commands
```bash
# Initialize foundation
cd bootstrap
just up

# Check status
just nvidia-smi
just argocd-password

# Access dashboard
open https://argocd.home.lab
```

For coding conventions, see [**AGENTS.md**](./AGENTS.md).

---

## License

MIT License © 2025 [Aaron]
