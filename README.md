# 🏠 homelab

A minimal yet modular **Kubernetes homelab** designed for reproducible local and edge deployments.  
This repository separates the lifecycle into two clear phases — **Bootstrap** and **Platform** —  
combining the simplicity of `Helmfile` for cluster provisioning with the reliability of `Argo CD` for GitOps management.

## Background

### From DevOps to AI Orchestration

The evolution of **DevOps** has always been driven by one goal — to accelerate delivery while maintaining reliability.  
It began as a cultural bridge between *developers* and *operations*, built on automation, CI/CD, and shared ownership.  
With the rise of the cloud, **GitOps** pushed this further by making infrastructure declarative and auditable —  
turning operations into a version-controlled, reproducible system of record.

Now, with the emergence of **AI-driven automation (AIOps)**, DevOps is transforming once again:  
from *manual orchestration* to *autonomous self-healing*,  
from *scripted pipelines* to *AI-assisted decision loops*,  
and from *operators of infrastructure* to *orchestrators of intelligence*.  

In this paradigm, DevOps engineers are no longer pipeline builders — they are **system conductors**, designing platforms that learn, adapt, and optimize themselves over time.

---

### Purpose of This Homelab

This repository is more than a **GitOps playground** — it’s a living experiment in **AI-native platform orchestration**.  
Its goal is to prototype an **autonomous infrastructure control plane** that can *sense, decide, and act*  
based on live metrics, events, and contextual data.

> ⚙️ *In short:* build a platform that can **operate itself**, not just **deploy itself.**

This homelab is designed to:
- **Prototype AIOps workflows** where metrics and models drive real-time adaptive behavior.  
- **Move beyond human-driven runbooks**, exploring autonomous remediation and intelligent scaling.  
- **Demonstrate the “DevOps as Orchestrator” mindset**, where engineers focus on system intelligence, not mechanical toil.  
- **Unify experimentation and reproducibility**, enabling rapid iteration with GitOps-level consistency.

Ultimately, it serves as a **personal testbed for AI-assisted infrastructure** —  
a place to explore how one engineer can achieve the orchestration capability of a 100-person SRE team.

---

### Direction: Building a Self-Evolving Platform

The homelab is structured to evolve progressively:

1. **Declarative Infrastructure** → Helmfile + Argo CD (GitOps baseline)  
2. **Event-Driven Automation** → Argo Workflows + Kyverno + Prometheus Alerts  
3. **Cognitive Operations (AIOps)** → LLM-based log analysis, auto-remediation, anomaly detection  
4. **Autonomous Orchestration** → self-optimizing deployments, networking, and scheduling decisions

> “The future DevOps is not an operator — it’s an **orchestrator of intelligence**.”

---

### Vision: Toward a Self-Evolving DevOps Platform

As AI automation and optimization mature, the natural next step is **simulation** —  
a phase where the platform doesn’t just respond or adapt, but actively **experiments with itself**.  

This homelab envisions an infrastructure that continuously learns from its own telemetry —  
metrics, traces, costs, and workloads — to simulate alternative futures and discover the most efficient path forward.  
By embedding simulation into the orchestration layer, the system can *predict* the impact of changes before applying them:

> “If ArgoCD sync runs every 10s, how does it affect CPU load?”  
> “What happens if Cilium switches from L2 to BGP routing?”  
> “Can GPU scheduling improve by forecasting utilization patterns?”  

Through these *digital twin* simulations, the platform evolves from a static automation engine  
into a **self-learning, self-optimizing organism** capable of reasoning about its own performance.

The long-term vision is to build a system where:
1. **AI automates** repetitive operations and responses.  
2. **Optimization loops** dynamically tune resources across hybrid environments.  
3. **Simulation models** evaluate strategies before execution.  
4. **Autonomous governance** enforces policies and makes explainable decisions.

At this stage, DevOps is no longer maintenance — it becomes **orchestration intelligence**,  
a partnership between human design and machine evolution.

This is the essence of **AIOps-driven orchestration**:  
a platform that not only runs services, but continuously learns **how to run them better**.

---

## Overview

| Phase | Directory | Tool | Purpose |
|--------|------------|------|----------|
| **1️⃣ Bootstrap** | [`/bootstrap`](./bootstrap) | 🧰 Helmfile | Cluster provisioning & base infrastructure setup |
| **2️⃣ Platform** | [`/platform`](./platform) | 🚀 Argo CD | GitOps-driven operations for apps, workloads, and etc. |

---

### Infrastructure Stack

#### Bootstraping

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

#### GitOps Platform Managements
(WIP)

## Features

- **MicroK8s-ready**: Optimized for single-node or lightweight multi-node clusters.  
- **Cilium eBPF Networking**: Secure and high-performance data plane.  
- **GitOps-first Design**: Declarative Argo CD App-of-Apps pattern.  
- **Infisical Operator Integration**: Secure external secret management.  
- **Modular Helmfile Releases**: Each infra component managed independently.  
- **Local & CI Friendly**: Easy testing and linting through Helmfile CLI.  

---

## Repository Structure

```
$ tree -L 6 .
.
├── bootstrap
│   ├── bases
│   │   ├── envs
│   │   │   └── home.yaml
│   │   ├── envs.yaml.gotmpl
│   │   └── helmDefaults.yaml
│   ├── charts
│   │   └── raw
│   │       ├── Chart.yaml
│   │       ├── templates
│   │       │   ├── _helpers.tpl
│   │       │   └── resources.yaml
│   │       └── values.yaml
│   ├── helmfile.yaml
│   ├── Justfile
│   └── releases
│       ├── argocd
│       │   ├── defaults.yaml
│       │   ├── helmfile.gotmpl
│       │   └── values
│       │       └── home.yaml.gotmpl
│       ├── cilium
│       │   ├── defaults.yaml
│       │   ├── helmfile.gotmpl
│       │   └── values
│       │       └── home.yaml.gotmpl
│       ├── gpu-operator
│       │   ├── defaults.yaml
│       │   ├── helmfile.gotmpl
│       │   └── values
│       │       └── home.yaml.gotmpl
│       └── infisical
│           ├── helmfile.gotmpl
│           └── values.yaml
├── docs
│   ├── architecture.md
│   └── README.md
├── platform
│   ├── gitops
│   │   ├── Chart.yaml
│   │   ├── templates
│   │   │   ├── appset-app.yaml
│   │   │   └── appset-pr.yaml
│   │   └── values.yaml
│   ├── Justfile
│   ├── projects
│   │   ├── cloud.yaml
│   │   └── home.yaml
│   └── stacks
│       ├── 00-core
│       │   └── overlays
│       │       ├── cloud
│       │       └── home
│       │           ├── cert-manager.yaml
│       │           ├── cloudflared.yaml
│       │           ├── coredns.yaml
│       │           ├── kyverno.yaml
│       │           ├── registry.yaml
│       │           └── tailscale.yaml
│       ├── 01-platforms
│       │   └── overlays
│       │       └── home
│       │           ├── argo-events.yaml
│       │           ├── argo-rollouts.yaml
│       │           ├── argo-workflows.yaml
│       │           └── authentik.yaml
│       ├── 02-o11y
│       │   └── overlays
│       │       ├── cloud
│       │       └── home
│       │           ├── grafana.yaml
│       │           ├── loki.yaml
│       │           ├── pyroscope.yaml
│       │           └── tempo.yaml
│       ├── 03-data
│       │   └── overlays
│       │       ├── cloud
│       │       └── home
│       │           ├── airbyte.yaml
│       │           ├── airflow.yaml
│       │           ├── clickhouse.yaml
│       │           ├── datahub.yaml
│       │           ├── postgres.yaml
│       │           ├── redis.yaml
│       │           ├── redpanda.yaml
│       │           └── scylladb.yaml
│       ├── 04-ml
│       │   └── overlays
│       │       ├── cloud
│       │       └── home
│       │           ├── minio.yaml
│       │           ├── ollama.yaml
│       │           ├── openlit.yaml
│       │           ├── qdrant.yaml
│       │           ├── ray.yaml
│       │           └── wandb.yaml
│       ├── 05-workloads
│       │   ├── charts
│       │   │   ├── drizzle
│       │   │   ├── mt5-trader
│       │   │   └── talk-ready
│       │   └── overlays
│       │       ├── cloud
│       │       └── home
│       │           ├── drizzle.yaml
│       │           ├── mt5-trader-x.yaml
│       │           ├── nextcloud.yaml
│       │           └── talk-ready.yaml
│       └── 06-labs
│           └── overlays
│               └── home
│                   ├── jupyterhub.yaml
│                   ├── n8n.yaml
│                   └── superset.yaml
└── README.md

51 directories, 65 files
````

---

## Quick Start

### 1. Prerequisites
- Ubuntu 24.04 or later
- MicroK8s or K3s installed
- `helm`, `helmfile`, and `kubectl` available
- Infisical account & API token

---

### 2. Bootstrap the Cluster

TODO:

### 3. Initialize Argo CD Root Application

---

Once Argo CD is deployed, register the GitOps ApplicationSets for Apps and PRs.

Then, Argo CD will automatically sync all defined core, platform, workloads and etc.

---

## Design Principles

* **Declarative Everything:** All infra and app states are stored in Git.
* **Two-phase lifecycle:** Helmfile for setup, Argo CD for operations.
* **Reproducibility:** Any cluster can be rebuilt with a single bootstrap command.
* **Extensibility:** Add or remove Helmfile releases and ArgoCD apps modularly.
* **Security-first:** Secrets are handled exclusively through Infisical.

---

## License

MIT License © 2025 [Aaron]

---

> *“Build locally. Automate globally.”*
> — homelab philosophy
