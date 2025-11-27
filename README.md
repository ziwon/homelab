# 🏠 homelab (A playground for AI Agents)

A modular Kubernetes homelab that evolves from GitOps automation to AI-driven orchestration, enabling reproducible, adaptive deployments across local and edge clusters.
(K3s + Helmfile + Argo CD + AIOps workflows)

---

## Overview

| Phase | Directory | Tool | Purpose |
|--------|------------|------|----------|
| **1️⃣ Bootstrap** | [`/bootstrap`](./bootstrap) | 🧰 Helmfile | Cluster provisioning & base infrastructure setup |
| **2️⃣ Platform** | [`/platform`](./platform) | 🚀 Argo CD | GitOps-driven operations for apps, workloads, and etc. |

---

## Features

- **MicroK8s-ready**: Optimized for single-node or lightweight multi-node clusters.  
- **Cilium eBPF Networking**: Secure and high-performance data plane.  
- **GitOps-first Design**: Declarative Argo CD App-of-Apps pattern.  
- **Infisical Operator Integration**: Secure external secret management.  
- **Modular Helmfile Releases**: Each infra component managed independently.  
- **Local & CI Friendly**: Easy testing and linting through Helmfile CLI.  

---

## Infrastructure

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Access                          │
├─────────────────────────────────────────────────────────────────┤
│  Tailscale VPN (Private DNS)     Cloudflared (Public DNS)       │
│  home.lab → Load Balancer        restack.tech → Tunnel → Pod    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Load Balancer Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  Gateway (x.x.x.x/30)      │    CoreDNS External (x.x.x.x/31)   │
│  HTTP/HTTPS Traffic        │    DNS Queries (home.lab)          │
│  Cilium L2 Announcements   │    Cilium L2 Announcements         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes (K3s) Cluster                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  Cilium CNI    │  │  Gateway API │  │  CoreDNS (Custom)  │   │
│  │  - eBPF Proxy  │  │  - Envoy     │  │  - home.lab zone   │   │
│  │  - L2 LB       │  │  - HTTPRoute │  │  - Split DNS       │   │
│  └────────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                 │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  ArgoCD        │  │  GPU Operator│  │  Infisical Operator│   │
│  │  - GitOps      │  │  - NVIDIA    │  │  - Secrets Mgmt    │   │
│  │  - CD Pipeline │  │  - Runtime   │  │  - Env Injection   │   │
│  └────────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## GitOps Platform Managements
```
                         ┌───────────────────────────────┐
                         │           GitHub              │
                         │                               │
                         │  ┌─────────────────────────┐  │
Dev Laptop               │  │ homelab repo            │  │
                         │  │ - argocd apps/          │  │
                         │  │ - helmfile/             │  │
   git push ─────────────┼──┤ - app-of-apps           │  │
                         │  └─────────────────────────┘  │
   git push ─────────────│  ┌─────────────────────────┐  │
 (code change)           │  │ landing-page repo       │  │
                         │  │ - app source            │  │
                         │  │ - Dockerfile            │  │
                         │  └─────────────────────────┘  │
   git push ─────────────│  ┌─────────────────────────┐  │
 (code change)           │  │ gpu-scheduler repo      │  │
                         │  │ - controller / webhook  │  │
                         │  │ - Dockerfile            │  │
                         │  └─────────────────────────┘  │
                         │                               │
                         │  GitHub Actions               │
                         │  ┌─────────────────────────┐  │
                         │  │ k8s-manifests-updater   │  │
                         │  │ (custom action)         │  │
                         │  └─────────────────────────┘  │
                         └──────────────┬────────────────┘
                                        │
                                        │ triggers CI
                                        ▼
                    ┌────────────────────────────────────────┐
                    │     K8s Cluster (home.lab)             │
                    │                                        │
                    │  ┌──────────────────────────────────┐  │
                    │  │ Actions Runner Controller (ARC)  │  │
                    |  | - AutoscalingRunnerSet           │  │
                    │  │ - self-hosted runners            │  │
                    │  └───────────────┬──────────────────┘  │
                    │                  │                     │
                    │                  ▼                    │
                    │        ┌───────────────────────┐       │
                    │        │     Buildkit Pods     │       │
                    │        │  (buildkitd executor) │       │
                    │        │                       │       │
                    │        │  buildctl build       │       │
                    │        │    cache-from:        │       │
                    │        │      harbor/...:buildcache    │
                    │        │    cache-to:          │       │
                    │        │      harbor/...:buildcache    │
                    │        └─────────┬────────────┘        │
                    │                  │                     │
                    │   OCI images     │   + cache layers    │
                    │        push      ▼                    │
                    │        ┌───────────────────────┐       │
                    │        │        Harbor         │       │
                    │        │ harbor.home.lab       │       │
                    │        │   landing-page:tag    │       │
                    │        │   gpu-scheduler:tag   │       │
                    │        │   buildcache:latest   │       │
                    │        └─────────┬────────────┘        │
                    │                  │                     |
                    │ k8s-manifests-updater (restack.ai[bot])│
                    │                  │  in app of apps YAML│
                    │                  ▼                    │
                    │  ┌──────────────────────────────────┐  │
                    │  │   homelab repo (GitHub)          │  │
                    │  │   - k8s manifests                │  │
                    │  │   - helm values (image tag)      │  │
                    │  └──────────────────────────────────┘  │
                    └───────────────────┬────────────────────┘
                                        │ Git pull (desired state)
                                        ▼
                       ┌────────────────────────────────┐
                       │             Argo CD            │
                       │  - App of Apps                 │
                       │  - Sync manifests              │
                       └───────────────┬────────────────┘
                                       │
                                       │ apply manifests
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │       Workload Namespaces               │
                  │  - landing-page deployment              │
                  │  - gpu-scheduler controller             │
                  │  - vector / quickwit / redpanda         │
                  │  - monitoring stack                     │
                  └─────────────────────────────────────────┘

```
## Observability
<img src="./docs/observability-stack.svg"/>

## Agent Ops

(Planning)
```
[User Browser]
    │
    ▼
[Agents UI (Playground Web)]
    │  HTTP
    ▼
[Agents API / Orchestrator]  ────→  [n8n Workflows]
    │                                   │
    │ events                            │ calls
    ▼                                   ▼
[Redpanda]  ←──── logs ──── [Vector]   [LLM / RAG / MCP Services]
    │                             │
    │ ingest                      │ traces / metrics
    ▼                             ▼
[Quickwit]                [VictoriaMetrics]   [Tempo]
    └──────────────┬───────────────┬────────────┘
                   ▼               ▼
                        [Grafana]
                   - Logs: Quickwit
                   - Metrics: VM
                   - Traces: Tempo
                   - APM/Periscope View
```
---

## License

MIT License © 2025 [Aaron]

---

> *“Build locally. Automate globally.”*
> — homelab philosophy
