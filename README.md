# 🏠 homelab (A playground for AI Agents)

A modular Kubernetes homelab that evolves from GitOps automation to AI-driven orchestration, enabling reproducible, adaptive deployments across local and edge clusters.
(K3s + Helmfile + Argo CD + AIOps workflows)

## Why a Homelab?

> Motivation: I bought a powerful desktop, only to realize the CPU and GPU were spending most of their time doing absolutely nothing. As an engineer, that kind of idle hardware triggers a deep urge to fix things. So this homelab was born:
> 
> A comparable AWS [g6.8xlarge](https://instances.vantage.sh/aws/ec2/g6.8xlarge?currency=USD&region=ap-northeast-2) runs $1,783/month On-Demand. My homelab cost less than that.

### Hardware Specs
- **CPU:** Intel Core Ultra 9 285K (2P + 8E + 14 LP-E cores @ 5.70 GHz)  
- **GPU:** NVIDIA Geforce RTX 5080 (84 SM for 10,752 CUDA cores)
- **NPU:** Intel AI Boost (Gen 3) — for when the GPU is busy and the CPU wants to pretend it's useful
- **RAM:** SANSUNG DDR5 5600 128 GB (32 GB x 4) — for peace of mind and aggressive multitasking



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
