# Homelab Bootstrap

A production-ready Kubernetes homelab powered by K3s, Cilium, and GitOps principles. This repository provides declarative infrastructure-as-code for a complete homelab stack with advanced networking, GPU support, and secrets management.

## Architecture Overview

### Infrastructure Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Access                           │
├─────────────────────────────────────────────────────────────────┤
│  Tailscale VPN (Split DNS)          Cloudflared (Public DNS)    │
│  home.lab → 172.16.0.202             restack.tech → Tunnel      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Load Balancer Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  Gateway (172.16.0.200)    │    CoreDNS External (172.16.0.202) │
│  HTTP/HTTPS Traffic        │    DNS Queries (home.lab)          │
│  Cilium L2 Announcements   │    Cilium L2 Announcements         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes (K3s) Cluster                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Cilium CNI    │  │  Gateway API │  │  CoreDNS (Custom)  │  │
│  │  - eBPF Proxy  │  │  - Envoy     │  │  - home.lab zone   │  │
│  │  - L2 LB       │  │  - HTTPRoute │  │  - Split DNS       │  │
│  └────────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  ArgoCD        │  │  GPU Operator│  │  Infisical Operator│  │
│  │  - GitOps      │  │  - NVIDIA    │  │  - Secrets Mgmt    │  │
│  │  - CD Pipeline │  │  - Runtime   │  │  - Env Injection   │  │
│  └────────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Network Architecture

**IP Allocation Strategy:**
- **Gateway Pool:** `172.16.0.200/31` (IPs: .200-.201)
  - `172.16.0.200` - Cilium Gateway (HTTP/HTTPS ingress)
  - `172.16.0.201` - Reserved for future use

- **DNS Pool:** `172.16.0.202/31` (IPs: .202-.203)
  - `172.16.0.202` - CoreDNS external LoadBalancer
  - `172.16.0.203` - Reserved for future use

**Traffic Flow:**

```
External Client (Tailscale)
    ↓
DNS Query: argocd.home.lab
    ↓
Tailscale Split DNS → 172.16.0.202 (CoreDNS)
    ↓
Response: 172.16.0.200
    ↓
HTTPS Request → 172.16.0.200 (Gateway)
    ↓
Cilium Gateway + Envoy
    ↓
HTTPRoute matches hostname
    ↓
Backend Service (argocd-server)
```

### DNS Strategy

**Private Domain (`home.lab`):**
- Served by CoreDNS running in the cluster
- Exposed via LoadBalancer at `172.16.0.202`
- Tailscale Split DNS configured to use this nameserver
- All `*.home.lab` queries resolve to `172.16.0.200` (Gateway)
- Accessible only within Tailscale VPN network

**Public Domain (`restack.tech`):**
- Served via Cloudflared tunnel
- Public internet access
- TLS termination at Gateway
- Optional: DNS managed by Cloudflare

### Secrets Management

All secrets, credentials, and environment variables are managed by **Infisical Operator**:

- **Secret Sources:**
  - API Keys, tokens, passwords
  - TLS certificates
  - Database credentials
  - OAuth client secrets

- **Injection Methods:**
  - Kubernetes Secrets (automatically synced)
  - Environment variables (injected into pods)
  - Volume mounts (file-based secrets)

- **Configuration:**
  - Project: `home-lab`
  - API: `https://app.infisical.com/api`
  - Authentication: Service account with client credentials

**Benefits:**
- ✅ No secrets in Git repository
- ✅ Centralized secret rotation
- ✅ Audit trail for secret access
- ✅ Fine-grained access control

## Components

### Core Infrastructure

**Cilium CNI** (`releases/cilium/`)
- eBPF-based networking and security
- kube-proxy replacement
- Gateway API integration with Envoy
- L2 announcements for LoadBalancer services
- Hubble for observability

**Gateway API** (`releases/cilium-post-setup/`)
- Kubernetes Gateway API implementation
- HTTPRoute-based routing
- TLS termination
- Multi-domain support (home.lab, restack.tech)

**CoreDNS Custom Configuration**
- Custom zone file for `home.lab`
- Wildcard DNS (`*.home.lab` → `172.16.0.200`)
- External LoadBalancer for Tailscale Split DNS
- File-based zone management

### GitOps & CD

**ArgoCD** (`releases/argocd/`)
- Declarative GitOps continuous delivery
- Application management
- Multi-cluster support (future)
- Web UI at `https://argocd.home.lab`

### GPU Workloads

**NVIDIA GPU Operator** (`releases/gpu-operator/`)
- Automated GPU node configuration
- NVIDIA Container Runtime
- Device plugin for GPU scheduling
- Requires pre-installed NVIDIA drivers on host

**Assumptions:**
- NVIDIA drivers installed at host level (version: `580.95.05`)
- RuntimeClass `nvidia` for GPU workloads
- Test with: `just k8s-nvidia-smi`

### Secrets Management

**Infisical Operator** (`releases/infisical/`)
- Syncs secrets from Infisical Cloud to Kubernetes
- Supports multiple environments
- Automatic secret rotation
- Integration with Kubernetes native secret store

## Prerequisites

### Required Software

- **K3s** (installed via `just up`)
- **Helmfile** - Kubernetes package orchestration
- **Just** - Command runner (alternative to Make)
- **kubectl** - Kubernetes CLI
- **Helm** - Package manager (used by Helmfile)

### Optional Tools

- **direnv** - Auto-load environment variables
- **Tailscale** - VPN for private network access
- **Cloudflared** - Cloudflare tunnel for public access

### Network Requirements

- Static IP range for LoadBalancer services (`172.16.0.200-203`)
- Network interface for L2 announcements (e.g., `enp130s0`)
- Ensure DHCP doesn't conflict with LoadBalancer IP range
- Tailscale mesh network configured

### GPU Requirements (Optional)

- NVIDIA GPU with compatible drivers
- Driver version: `580.95.05` or compatible
- Installed at host level before deploying gpu-operator

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd homelab/bootstrap
```

### 2. Configure Environment

Create your environment file based on `.env.home`:

```bash
# Copy and edit environment variables
cp .env.home .env.myenv
vim .env.myenv

# Key variables to configure:
# - DOMAIN_PRIVATE (e.g., home.lab)
# - DOMAIN_PUBLIC (e.g., your-domain.com)
# - L2_BRIDGE_INTERFACE (your network interface)
# - INFISICAL_* (Infisical credentials)
```

**Important:** Never commit `.env.*` files to Git. They contain sensitive credentials.

### 3. Bootstrap K3s Cluster

```bash
# Load environment
source .env.myenv

# Install K3s with custom configuration
just up

# Verify cluster is running
kubectl get nodes
```

### 4. Deploy Infrastructure

```bash
# List all releases
ENV=myenv just list

# Deploy everything
ENV=myenv just sync

# Or deploy specific components
ENV=myenv just sync-target cilium
ENV=myenv just sync-target argocd
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -A

# Check Gateway is programmed
kubectl get gateway cilium -n infra

# Check DNS is working
dig argocd.home.lab @172.16.0.202 +short
# Should return: 172.16.0.200

# Check HTTPRoutes
kubectl get httproute -A
```

### 6. Configure Tailscale Split DNS

In Tailscale admin console:

1. Go to **DNS** → **Nameservers**
2. Add nameserver: `172.16.0.202`
3. Restrict to domain: `home.lab`
4. Save

Or via CLI:
```bash
tailscale set --accept-dns --nameserver=172.16.0.202
```

Now all Tailscale clients can access `*.home.lab` services!

## Common Operations

### Managing Releases

```bash
# Template releases (dry-run)
ENV=home just template

# Template specific release
ENV=home just template-target cilium

# Sync all releases
ENV=home just sync

# Sync specific release
ENV=home just sync-target argocd

# Apply (create or update)
ENV=home just apply-target gpu-operator
```

### Testing

```bash
# Test GPU access
just k8s-nvidia-smi

# Test DNS resolution
dig test.home.lab @172.16.0.202

# Check Gateway health
kubectl get gateway cilium -n infra

# Check Cilium status
kubectl get pods -n kube-system -l k8s-app=cilium
```

### Generating Certificates

```bash
# Generate self-signed cert for development
just gen-certs home.lab

# Certificates will be created in secrets/ directory
# - secrets/home.lab.crt
# - secrets/home.lab.key
```

**Note:** For production, use proper certificates from Let's Encrypt or your CA.

### Secrets Management with Infisical

All secrets are managed externally via Infisical:

1. Add secrets to Infisical project (`home-lab`)
2. Infisical Operator automatically syncs to Kubernetes
3. Reference secrets in manifests:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    env:
    - name: API_KEY
      valueFrom:
        secretKeyRef:
          name: infisical-sync-secret
          key: API_KEY
```

## Directory Structure

```
.
├── bases/                          # Global configuration
│   ├── helmDefaults.yaml           # Default Helm settings
│   ├── envs.yaml.gotmpl            # Environment definitions
│   └── envs/                       # Per-environment configs
│       ├── home.yaml               # Home environment
│       └── ocp.yaml                # OpenShift environment
│
├── releases/                       # Component releases
│   ├── argocd/                     # ArgoCD GitOps
│   ├── cilium/                     # Cilium CNI
│   ├── cilium-post-setup/          # Gateway, DNS, L2 config
│   ├── gpu-operator/               # NVIDIA GPU Operator
│   └── infisical/                  # Infisical secrets operator
│
├── charts/                         # Local Helm charts
│   └── raw/                        # Raw manifest renderer
│
├── hacks/                          # Operational scripts
│   └── install-gateway-api-crds.sh # Gateway API CRD installer
│
├── secrets/                        # Generated secrets (gitignored)
│   ├── home.lab.crt                # TLS certificate
│   └── home.lab.key                # TLS private key
│
├── helmfile.yaml                   # Root Helmfile
├── Justfile                        # Command definitions
├── CLAUDE.md                       # AI assistant guidance
└── README.md                       # This file
```

## Helmfile Structure

Each release follows this pattern:

```
releases/<component>/
├── helmfile.gotmpl                 # Release definition
├── default.yaml                    # Base values
└── values/
    ├── home.yaml.gotmpl            # Home environment overrides
    └── ocp.yaml.gotmpl             # OCP environment overrides
```

**Release execution order:**
1. Cilium (layer: network)
2. Cilium post-setup (Gateway, DNS, L2)
3. GPU Operator (if enabled)
4. Infisical Operator (secrets management)
5. ArgoCD (layer: gitops)

## Environment Configuration

Environment-specific settings are managed in `bases/envs/<env>.yaml`:

```yaml
cilium:
  installed: true
  chart_version: 1.18.2

argocd:
  installed: true
  chart_version: 8.6.4

gpu-operator:
  installed: true
  chart_version: 25.3.4
```

To enable/disable components, set `installed: false`.

## Adding New Services

### 1. Add HTTPRoute

Edit `releases/cilium-post-setup/values/home.yaml.gotmpl`:

```yaml
- apiVersion: gateway.networking.k8s.io/v1
  kind: HTTPRoute
  metadata:
    name: my-service
    namespace: my-namespace
  spec:
    parentRefs:
      - name: cilium
        namespace: infra
    hostnames:
      - myservice.home.lab
    rules:
      - backendRefs:
          - name: my-service
            port: 80
```

### 2. Add DNS Record

Update the zone file in `releases/cilium-post-setup/values/home.yaml.gotmpl`:

```yaml
home.lab.db: |
  # ... existing records ...
  myservice    IN A     172.16.0.200
```

### 3. Sync Changes

```bash
ENV=home just sync-target cilium-post-setup
kubectl rollout restart deployment/coredns -n kube-system
```

## Troubleshooting

### Gateway Not Getting IP

```bash
# Check IP pools
kubectl get ciliumloadbalancerippool -o wide

# Check L2 announcement policies
kubectl get ciliuml2announcementpolicy -A

# Check Gateway status
kubectl describe gateway cilium -n infra
```

### DNS Not Resolving

```bash
# Check CoreDNS is running
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check custom ConfigMap
kubectl get configmap coredns-custom -n kube-system -o yaml

# Test DNS from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup argocd.home.lab 10.142.0.10

# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns
```

### HTTPRoute Not Working

```bash
# Check HTTPRoute status
kubectl get httproute -A

# Check Gateway listeners
kubectl get gateway cilium -n infra -o yaml

# Check Envoy service
kubectl get svc -n infra cilium-gateway-cilium

# Check Cilium Gateway controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=cilium-operator
```

### Secrets Not Syncing

```bash
# Check Infisical operator logs
kubectl logs -n infisical-operator-system \
  -l app.kubernetes.io/name=infisical-operator

# Verify Infisical credentials
kubectl get secret -n infisical-operator-system

# Check InfisicalSecret resources
kubectl get infisicalsecret -A
```

## Security Considerations

### Secrets Management

- ✅ All secrets stored in Infisical (never in Git)
- ✅ `.gitignore` prevents accidental credential commits
- ✅ Environment files (`.env.*`) are excluded from Git
- ✅ TLS certificates auto-generated and stored in `secrets/`

### Network Security

- Gateway enforces TLS termination
- Private domain accessible only via Tailscale VPN
- Cilium Network Policies (optional, add as needed)
- L2 LoadBalancer IPs isolated from DHCP range

### Access Control

- ArgoCD RBAC with readonly default policy
- Kubernetes RBAC for service accounts
- Infisical project-level access control
- Tailscale ACLs for network access

## Monitoring & Observability

### Hubble UI

Cilium's Hubble provides network observability:

```bash
# Access Hubble UI
open https://hubble.home.lab
```

### ArgoCD Dashboard

Monitor application deployments:

```bash
# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Access ArgoCD UI
open https://argocd.home.lab
```

## Roadmap

- [ ] Multi-cluster management with ArgoCD
- [ ] External-DNS integration for automatic DNS updates
- [ ] Cert-manager for automated TLS certificate management
- [ ] Prometheus + Grafana for metrics
- [ ] Loki for log aggregation
- [ ] Velero for backup and disaster recovery
- [ ] Cilium Network Policies for micro-segmentation

## Contributing

This is a personal homelab repository. Feel free to fork and adapt for your own use.

## License

MIT License - See LICENSE file for details

## References

- [K3s Documentation](https://docs.k3s.io/)
- [Cilium Documentation](https://docs.cilium.io/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Infisical Documentation](https://infisical.com/docs)
- [Helmfile Documentation](https://helmfile.readthedocs.io/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
