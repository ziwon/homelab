# Homelab - AI-Driven Kubernetes Platform

> A modular Kubernetes homelab that evolves from GitOps automation to AI-driven orchestration.
> (K3s + Helmfile + Argo CD + AIOps workflows)

## Communication Style

- Call me Aaron. 
- When conversing in Korean, use casual/informal speech (평어) instead of formal/polite speech (존댓말). Keep responses concise and direct for faster communication.

## Rules Reference

- ArgoCD App Templates: @.claude/rules/argocd-apps.md
- Kubernetes Rules: @.claude/rules/kubernetes.md
- Coding Style: @.claude/rules/coding-style.md

## Project Overview

This project is an enterprise-grade Kubernetes platform with a 2-phase deployment pipeline:

1. **Bootstrap (Phase 1)**: Cluster base infrastructure setup with Helmfile
2. **Platform (Phase 2)**: Application deployment and management via Argo CD GitOps

### Hardware Specs
- **CPU**: Intel Core Ultra 9 285K (8P + 16E + 14 LP-E cores @ 5.70 GHz)
- **GPU**: NVIDIA GeForce RTX 5080 (16GB VRAM)
- **RAM**: 128GB DDR5-5600
- **Storage**: XFS volumes (/cache, /data)

## Directory Structure

```
homelab/
├── bootstrap/              # Phase 1: Helmfile-based cluster initialization
│   ├── helmfile.yaml       # Main Helmfile
│   ├── Justfile            # Task automation (just up, just sync, etc.)
│   ├── releases/           # Helm release definitions
│   │   ├── argocd/         # GitOps engine
│   │   ├── cilium/         # eBPF CNI
│   │   ├── gpu-operator/   # NVIDIA GPU
│   │   └── infisical/      # Secret management
│   └── bases/              # Common settings
│
├── platform/               # Phase 2: Argo CD App-of-Apps
│   ├── gitops/             # ApplicationSet templates
│   ├── projects/           # ArgoCD projects (home, cloud)
│   └── stacks/             # Kustomize Overlay pattern
│       ├── 00-core/        # Core infrastructure (cert-manager, cloudflared, tailscale)
│       ├── 01-platforms/   # Platform services (argo-workflows, harbor, buildkit)
│       ├── 02-o11y/        # Observability (grafana, tempo, quickwit)
│       ├── 03-data/        # Databases (postgres, redis, clickhouse, redpanda)
│       ├── 04-ml/          # ML services (feast, mlflow, ray, qdrant)
│       ├── 05-workloads/   # Applications (deepfx, mt5-trader)
│       └── 06-labs/        # Experimental (jupyterhub, n8n, superset)
│
└── docs/                   # Architecture documentation
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Cluster | K3s | Lightweight Kubernetes |
| CNI | Cilium eBPF | High-performance networking + L2 LB |
| Ingress | Gateway API + Envoy | HTTP routing |
| GitOps | Argo CD | Declarative CD |
| Secrets | Infisical Operator | Environment variable injection |
| GPU | NVIDIA GPU Operator | CUDA runtime |
| Observability | Grafana, VictoriaMetrics, Tempo, Quickwit | Monitoring |
| Data | PostgreSQL, Redis, ClickHouse, Redpanda | Data storage |
| ML | Feast, MLFlow, Ray, Qdrant | ML platform |

## Common Commands

### Bootstrap (Helmfile)
```bash
cd bootstrap
just up              # Install K3s cluster
just down            # Remove K3s cluster
just sync            # Sync Helmfile (all releases)
just nvidia-smi      # Check GPU status
just argocd-password # Get ArgoCD password
```

### Kubernetes
```bash
export KUBECONFIG=$HOME/.kube/config.home
kubectl get pods -A
kubectl get applications -n argocd
argocd app list
```

### Platform
```bash
cd platform
# ArgoCD auto-syncs Git changes
# Manual sync: argocd app sync <app-name>
```

## Coding Conventions

### YAML Files
- Indentation: 2 spaces
- Strings: Use quotes only for special characters
- Comments: Add only for complex configurations

### Helm Values
- Environment separation: `values/default.yaml`, `values/home.yaml`
- For gotmpl: Use `.yaml.gotmpl` extension

### Kustomize Overlays
- Path pattern: `platform/stacks/{NN}-{category}/overlays/{environment}/{app}.yaml`
- Environments: `home`, `cloud`, `disabled`

### ArgoCD Applications
```yaml
apps:
  - name: app-name
    namespace: target-namespace
    chart: chart-name
    repoURL: https://helm.repo.io
    targetRevision: "1.0.0"
    values: |
      key: value
```

## Architecture Patterns

### App-of-Apps
- `apps-home.yaml` → `gitops/` Chart → `ApplicationSet` → Individual Applications
- Matrix Generator auto-scans `platform/stacks/*/overlays/home/*.yaml`

### GPU Partitioning (NVIDIA MPS + Ray)
- MPS: GPU memory sharing (16GB → 16 × 1GB logical units)
- Ray: Distributed task scheduling (P-cores: GPU, E-cores: Control Plane)

### Feature Store (Feast + ClickHouse + Redis)
- Online Store: Redis (< 1ms latency)
- Offline Store: ClickHouse (analytical queries)
- Registry: PostgreSQL

## Important Notes

### Secret Management
- Use Infisical Operator
- Never commit `.env` files
- `bootstrap/secrets/` directory must be encrypted

### Networking
- Private DNS: `home.lab` (Tailscale + CoreDNS)
- Public DNS: `restack.tech` (Cloudflare Tunnel)
- L2 LB: Cilium L2 Announcements

### Environment Separation
- `home`: Local homelab (primary)
- `cloud`: Cloud environment (future)
- `disabled`: Deactivated apps

## Troubleshooting

### ArgoCD Sync Failure
```bash
argocd app get <app-name>
argocd app sync <app-name> --prune
```

### GPU Issues
```bash
kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset
nvidia-smi
```

### Helmfile Issues
```bash
cd bootstrap
helmfile -e home diff
helmfile -e home sync --debug
```
