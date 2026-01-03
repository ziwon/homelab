# 🏠 Homelab

[![K3s](https://img.shields.io/badge/K3s-Kubernetes-326CE5?logo=kubernetes)](https://k3s.io/)
[![ArgoCD](https://img.shields.io/badge/Argo%20CD-GitOps-EF7B4D?logo=argo)](https://argoproj.github.io/cd/)
[![NVIDIA](https://img.shields.io/badge/RTX%205080-GPU-76B900?logo=nvidia)](https://www.nvidia.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Kubernetes platform for AI/ML workloads. K3s cluster with GitOps automation.

## Hardware

| Component | Spec |
|-----------|------|
| CPU | Intel Core Ultra 9 285K (8P + 16E cores) |
| GPU | NVIDIA RTX 5080 16GB |
| RAM | 128GB DDR5-5600 |
| Storage | XFS (/cache, /data) |

Comparable to AWS g6.8xlarge (~$1,780/month).

## Directory Structure

```
homelab/
├── bootstrap/          # Phase 1: Helmfile cluster init
│   ├── helmfile.yaml
│   ├── Justfile
│   └── releases/       # argocd, cilium, gpu-operator, infisical
├── platform/           # Phase 2: Argo CD GitOps
│   ├── gitops/         # ApplicationSet templates
│   └── stacks/         # Kustomize overlays (00-core ~ 06-labs)
└── docs/               # Architecture docs
```

## Architecture

Two-phase deployment:

```
Phase 1: Bootstrap (Helmfile)
├── K3s cluster
├── Cilium eBPF CNI
├── GPU Operator
└── Infisical secrets

Phase 2: Platform (Argo CD)
├── 00-core      # cert-manager, cloudflared, tailscale
├── 01-platforms # argo-workflows, harbor, buildkit
├── 02-o11y      # grafana, tempo, quickwit
├── 03-data      # postgres, redis, clickhouse, redpanda
├── 04-ml        # feast, mlflow, ray, qdrant
├── 05-workloads # deepfx, mt5-trader
└── 06-labs      # jupyterhub, n8n, superset
```

## Stack

| Layer | Tech |
|-------|------|
| Cluster | K3s |
| Network | Cilium eBPF + Gateway API |
| GitOps | Argo CD (App-of-Apps) |
| Secrets | Infisical Operator |
| GPU | NVIDIA MPS + Ray |
| Observability | VictoriaMetrics, Tempo, Pyroscope, Quickwit, Grafana |
| Data | PostgreSQL, Redis, ClickHouse, Redpanda |
| ML | Feast, MLflow, Ray, Qdrant |

## GPU Partitioning

NVIDIA MPS splits RTX 5080 into 16 logical units (1GB each). Ray schedules workloads across hybrid cores:

- **P-cores (0-7)**: GPU tasks, training, inference
- **E-cores (8-23)**: Control plane, scheduling

See [GPU Partitioning](./docs/gpu-partitioning.md).

## Observability

```
Logs:    Vector → Redpanda → Quickwit → Grafana
Metrics: Prometheus → VictoriaMetrics → Grafana
Traces:  OTel SDK → Alloy → Tempo → Grafana
APM:     Pyroscope (service map, trace-log correlation, error analysis)
```

## Quick Start

### Prerequisites

- [just](https://github.com/casey/just) - Command runner
- [helmfile](https://github.com/helmfile/helmfile) - Helm release management
- [kubectl](https://kubernetes.io/docs/reference/kubectl/) - Kubernetes CLI

### Bootstrap

```bash
cd bootstrap
just up
just nvidia-smi
just argocd-password

export KUBECONFIG=$HOME/.kube/config.home
kubectl get pods -A
open https://argocd.home.lab
```

## Networking

| Domain | Method |
|--------|--------|
| `*.home.lab` | Tailscale + CoreDNS |
| `*.restack.tech` | Cloudflare Tunnel |

## AI Operations

GitHub Actions runners (ARC) with Claude integration:

- Issue analysis and PR generation
- Code review for security and performance
- Manifest validation

### Dynamic Skill Loading

Skills are loaded on-demand based on issue content keywords:

| Skill | Trigger Keywords |
|-------|-----------------|
| `argocd-generator` | deploy, helm, chart, 배포 |
| `troubleshoot` | error, crash, pending, 에러 |
| `kubernetes-review` | review, validate, yaml, 리뷰 |
| `infisical-manager` | secret, env, 시크릿 |

Only relevant skills (max 2) are loaded per request, reducing prompt size and token usage.

### Multi-LLM Routing

- Local (Qwen): Privacy-sensitive tasks
- Cloud (Claude, Gemini): Complex reasoning

## Docs

- [System Architecture](./docs/architecture.md)
- [GPU Partitioning](./docs/gpu-partitioning.md)
- [Feature Store](./docs/feature-store.md)
- [Observability](./docs/observability.md)
- [Agent Instructions](./AGENTS.md)

## License

MIT
