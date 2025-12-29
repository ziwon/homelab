# 🏠 Homelab: AI-Driven Kubernetes Platform

> **Build locally. Automate globally.**  
> A modular Kubernetes homelab designed for high-performance AI workloads, evolving from GitOps automation to autonomous AI-driven orchestration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![K3s](https://img.shields.io/badge/Kubernetes-K3s-blue?logo=kubernetes)](https://k3s.io/)
[![ArgoCD](https://img.shields.io/badge/GitOps-Argo%20CD-orange?logo=argo)](https://argoproj.github.io/cd/)
[![NVIDIA](https://img.shields.io/badge/GPU-NVIDIA%20RTX%205080-green?logo=nvidia)](https://www.nvidia.com)

---

## 📝 Motivation

This project began as an effort to efficiently utilize high-performance hardware (Intel Core Ultra 9, NVIDIA RTX 5080) that would otherwise remain idle. It focuses on building a stable, reproducible Kubernetes environment to host personal AI research and automation workflows. 

### 💰 Cost Efficiency
Maintaining local hardware offers significant long-term savings compared to equivalent cloud resources. For instance, an AWS [g6.8xlarge](https://instances.vantage.sh/aws/ec2/g6.8xlarge?currency=USD&region=ap-northeast-2) instance—which provides comparable compute and GPU capacity—costs approximately **$1,780/month** on-demand. This homelab provides a similar performance profile for a one-time hardware investment.

---

## 💻 Hardware

| Component | Specification | Highlight |
| :--- | :--- | :--- |
| **CPU** | Intel Core Ultra 9 285K | 24 Cores (8P + 16E) up to 5.70 GHz |
| **GPU** | NVIDIA GeForce RTX 5080 | 16GB VRAM, 10,752 CUDA Cores |
| **NPU** | Intel AI Boost (Gen 3) | Specialized AI acceleration |
| **RAM** | 128GB DDR5-5600 | High-capacity Samsung modules |
| **Networking**| Tailscale + Cilium eBPF | Encrypted Mesh + High-perf CNI |

---

## 🏗️ Architecture: Two-Phase Deployment

The platform is built on a clean separation of concerns, ensuring stability and reproducibility.

### Phase 1: Bootstrap (The Foundation)
Managed via **Helmfile** for rapid cluster initialization.
- **Tools**: `K3s`, `Cilium`, `Infisical`, `GPU Operator`.
- **Directory**: [`/bootstrap`](./bootstrap)

### Phase 2: Platform (The Workloads)
Managed via **Argo CD** App-of-Apps pattern (GitOps).
- **Stacks**: Core Infra, O11y, Data, ML/AI, Application Workloads.
- **Directory**: [`/platform`](./platform)

---

## 🤖 AI-Powered Operations

This lab goes beyond simple automation, integrating advanced AI agents directly into the operational loop.

### 🔄 Autonomous AI Ops (ARC + Claude)
We utilize **Actions Runner Controller (ARC)** to host self-hosted Kubernetes runners. These runners execute **Claude-powered workflows** that:
- **Auto-Resolve Issues**: Labeled issues are analyzed and fixed via PRs automatically.
- **Intelligent PR Reviews**: Claude reviews code for security (OWASP), performance, and manifest correctness.
- **In-Cluster Context**: Agents have gated read access to cluster state via `kubectl` to verify deployment health.

### 🧠 Hybrid AI Strategy
A security-conscious, high-performance approach to LLM integration:
- **Local (GPT-OSS / Qwen)**: Runs on-prem for high-privacy tasks and basic code analysis.
- **Cloud (Claude / Gemini)**: Leveraged for complex research and high-order reasoning via secure workflows.

---

## ⚙️ Advanced GitOps Engine

The heart of the platform's automation is a sophisticated **ArgoCD ApplicationSet** engine.

### 🧩 Zero-Touch Service Discovery
Our [ApplicationSet](./platform/gitops/templates/appset-app.yaml) uses a **Matrix Generator** that auto-scans the repository for YAML definitions.
- **Matrix Generation**: Combines Git file discovery with dynamic list elements.
- **Go Template Orchestration**: Deeply uses Go templates to automate sync waves, dependency management, and resource patching based on file structure.
- **Infisical Integration**: native secret injection without committing sensitive data.

---

## 👾 AI & ML Orchestration

Specifically tuned for modern AI workflows, featuring advanced resource partitioning.

### 💠 Hybrid Resource Partitioning (NVIDIA MPS + Ray)
We optimize the **Intel Hybrid Architecture** by pinning Ray Head to E-cores and Ray Workers to P-cores, while using **NVIDIA Multi-Process Service (MPS)** to slice the GPU into 16 logical units.

> [!TIP]
> This allows running 16 concurrent inference tasks (1GB each) on a single RTX 5080 without performance degradation.
> See [GPU Architecture Docs](./docs/gpu-partitioning-architecture.md).

---

## 📉 Observability & Insights

Complete visibility from kernel-level eBPF traces to application-level APM.

![Observability Stack](./docs/observability-stack.svg)

- **Logs**: Vector → Redpanda → Quickwit (Cost-efficient S3 storage)
- **Metrics**: VictoriaMetrics (Prometheus-compatible)
- **Traces**: Grafana Tempo
- **Visualization**: Unified Grafana Dashboards

---

## 🛠️ Developer Guide

### Prerequisites
- [Just](https://github.com/casey/just) (Task runner)
- [Helmfile](https://github.com/helmfile/helmfile)
- [Kubectl](https://kubernetes.io/docs/reference/kubectl/)

### Quick Start
```bash
# 1. Initialize the cluster foundation
cd bootstrap
just up

# 2. Check cluster status
just nvidia-smi
just argocd-password

# 3. Access GitOps Dashboard
open https://argocd.home.lab
```

For detailed agent rules and coding conventions, see [**AGENTS.md**](./AGENTS.md).

---

## 📜 License

MIT License © 2025 [Aaron]

