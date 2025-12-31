# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Homelab Platform                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Phase 2: Platform (Argo CD)                 │    │
│  │                                                                     │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │ 00-core  │ │01-platfrm│ │ 02-o11y  │ │ 03-data  │ │  04-ml   │   │    │
│  │  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤   │    │
│  │  │cert-mgr  │ │argo-wf   │ │grafana   │ │postgres  │ │feast     │   │    │
│  │  │cloudflare│ │harbor    │ │tempo     │ │redis     │ │mlflow    │   │    │
│  │  │tailscale │ │buildkit  │ │quickwit  │ │clickhouse│ │ray       │   │    │
│  │  │          │ │          │ │pyroscope │ │redpanda  │ │qdrant    │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  │                                                                     │    │
│  │  ┌──────────┐ ┌──────────┐                                          │    │
│  │  │05-wrklod │ │ 06-labs  │    ApplicationSet (Matrix Generator)     │    │
│  │  ├──────────┤ ├──────────┤    Scans: platform/stacks/*/overlays/*   │    │
│  │  │deepfx    │ │jupyterhub│                                          │    │
│  │  │mt5-trader│ │n8n       │                                          │    │
│  │  │          │ │superset  │                                          │    │
│  │  └──────────┘ └──────────┘                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Phase 1: Bootstrap (Helmfile)                 │    │
│  │                                                                     │    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │    │
│  │  │    K3s       │ │   Cilium     │ │ GPU Operator │ │ Infisical  │  │    │
│  │  │  Cluster     │ │  eBPF CNI    │ │    CUDA      │ │  Secrets   │  │    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              Hardware Layer                                 │
│  CPU: Intel Core Ultra 9 285K    GPU: RTX 5080 16GB    RAM: 128GB DDR5      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Deployment Phases

### Phase 1: Bootstrap

Helmfile-based cluster initialization. Installs foundational components required before GitOps takes over.

| Component | Purpose |
|-----------|---------|
| K3s | Lightweight Kubernetes distribution |
| Cilium | eBPF-based CNI with L2 load balancing |
| GPU Operator | NVIDIA driver and CUDA runtime |
| Infisical | Secret management operator |

```bash
cd bootstrap
just up        # Install cluster
just sync      # Apply Helmfile releases
```

### Phase 2: Platform

Argo CD manages all application deployments via App-of-Apps pattern.

```
apps-home.yaml → gitops/ Chart → ApplicationSet → Individual Applications
                                        │
                                        ▼
                    Matrix Generator scans:
                    platform/stacks/*/overlays/home/*.yaml
```

Each stack directory contains Kustomize overlays:

| Stack | Purpose | Examples |
|-------|---------|----------|
| 00-core | Infrastructure | cert-manager, cloudflared, tailscale |
| 01-platforms | Platform services | argo-workflows, harbor, buildkit |
| 02-o11y | Observability | grafana, tempo, quickwit, pyroscope |
| 03-data | Databases | postgres, redis, clickhouse, redpanda |
| 04-ml | ML platform | feast, mlflow, ray, qdrant |
| 05-workloads | Applications | deepfx, mt5-trader |
| 06-labs | Experimental | jupyterhub, n8n, superset |

## Networking

```
                    Internet
                        │
            ┌───────────┴───────────┐
            │                       │
    ┌───────▼───────┐      ┌──────▼──────┐
    │   Cloudflare   │      │  Tailscale   │
    │    Tunnel      │      │    Mesh      │
    │ *.restack.tech │      │  *.home.lab  │
    └───────┬────────┘      └──────┬───────┘
            │                      │
            └──────────┬───────────┘
                       │
              ┌────────▼────────┐
              │  Cilium Gateway  │
              │   (Envoy L7)     │
              └────────┬─────────┘
                       │
              ┌────────▼────────┐
              │   K3s Cluster    │
              └──────────────────┘
```

| Domain | Access Method |
|--------|---------------|
| `*.home.lab` | Tailscale + CoreDNS (private) |
| `*.restack.tech` | Cloudflare Tunnel (public) |

## Storage

XFS volumes optimized for different workloads:

| Mount | Purpose | Optimization |
|-------|---------|--------------|
| `/cache` | Build cache, MPS pipe, Ray spill | Large inode (1024), filestreams |
| `/data` | ML datasets, checkpoints, models | Large extent allocation (256MB) |

## Secret Management

All secrets managed via Infisical Operator:

```yaml
# InfisicalSecret injects env vars into pods
spec:
  authentication:
    universalAuth:
      secretsScope:
        projectSlug: homelab
        envSlug: prod
        secretsPath: "/{app-name}"
```

No `.env` files in Git. Secrets synced from Infisical cloud.

## Related Docs

- [GPU Partitioning](./gpu-partitioning.md) - MPS + Ray resource allocation
- [Feature Store](./feature-store.md) - Feast architecture
- [Observability](./observability.md) - Monitoring stack
