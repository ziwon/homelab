---
name: argocd-generator
description: Generates ArgoCD Application manifests following the App-of-Apps pattern. Use when creating new applications, deploying services, or adding apps to the homelab platform.
---

# ArgoCD Application Generator

Generate ArgoCD applications following the App-of-Apps pattern.

## CRITICAL: Helm Chart Values Analysis

**Before creating any Helm-based application, you MUST:**

1. **Fetch and analyze the chart's values.yaml** from the official repository
2. **Understand all available configuration options** - do NOT use minimal/placeholder values
3. **Configure production-ready settings** including:
   - Database connections (PostgreSQL, Redis, etc.)
   - Persistence/storage settings
   - Authentication and security settings
   - Resource requests/limits appropriate for the workload
   - Service configuration
   - Environment-specific settings for homelab

**DO NOT** create oversimplified values like:
```yaml
# BAD - Too minimal, missing critical configuration
values: |
  replicaCount: 1
  service:
    type: ClusterIP
    port: 8080
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
```

**DO** analyze the chart thoroughly and configure properly:
```yaml
# GOOD - Properly configured based on chart analysis
values: |
  replicaCount: 1

  # Database configuration (if chart supports it)
  postgresql:
    enabled: false  # Use external PostgreSQL

  extraEnvVars:
    - name: DATABASE_HOST
      value: cluster-pg-db-pgbouncer.postgres.svc
    - name: DATABASE_PORT
      value: "5432"

  extraEnvVarsSecret: superset-managed-secrets

  persistence:
    enabled: true
    size: 10Gi
    storageClassName: local-path

  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi
```

---

## How to Use This Template

1. Extract values from the issue:
   - `helm repo add NAME URL` -> use URL as repoURL
   - Chart version mentioned -> use as targetRevision
   - **If issue provides values.yaml content, use it EXACTLY as provided**
   - Any custom values mentioned -> add to values section

2. Fill in ALL fields - never leave placeholders like `{app-name}`

3. The `values:` section:
   - **PRIORITY 1**: If the issue includes values.yaml content, copy it exactly
   - **PRIORITY 2**: If no values provided, **fetch and analyze the chart's values.yaml first**
   - Configure all relevant sections based on the chart's capabilities
   - The examples below are ONLY structural references, not complete configurations

## CRITICAL: Single File Per Application

**All resources for the same application MUST be in a single YAML file.**

The App-of-Apps pattern is designed to manage multiple related resources (Helm chart, InfisicalSecret, HTTPRoute, etc.) within the same context. Resources that share:
- Same namespace
- Same concern/purpose
- Same microservice

**MUST** all be defined in ONE file: `{app-name}.yaml`

**DO NOT** create separate files like:
```
# BAD - Multiple files for same app
superset-raw.yaml      # InfisicalSecret
superset.yaml          # Helm chart
superset-routes.yaml   # HTTPRoute
```

**DO** put everything in a single file:
```
# GOOD - Single file with all related resources
superset.yaml          # Contains: InfisicalSecret + Helm chart + HTTPRoute (if needed)
```

Example structure in the single file:
```yaml
apps:
  # Raw resources (InfisicalSecret, etc.) - deploy first
  - name: superset-raw
    namespace: superset
    syncWave: "5"
    source:
      # ... InfisicalSecret definition

  # Main Helm chart - deploy after raw resources
  - name: superset
    namespace: superset
    syncWave: "10"
    dependencies:
      - superset-raw
    source:
      # ... Helm chart definition
```

---

## Stack Categories

| Stack | Path | Purpose |
|-------|------|---------|
| 00-core | `platform/stacks/00-core/` | Core infra (cert-manager, cloudflared) |
| 01-platforms | `platform/stacks/01-platforms/` | Platform services (argo-workflows, harbor) |
| 02-o11y | `platform/stacks/02-o11y/` | Observability (grafana, tempo) |
| 03-data | `platform/stacks/03-data/` | Databases (postgres, redis) |
| 04-ml | `platform/stacks/04-ml/` | ML services (feast, ray, mlflow) |
| 05-workloads | `platform/stacks/05-workloads/` | Applications |
| 06-labs | `platform/stacks/06-labs/` | Experimental |

## File Location

**One file per application:**
```
platform/stacks/{NN}-{category}/overlays/home/{app-name}.yaml
```

## App-of-Apps Source Types

This project supports 3 types of application sources:

| Type | Use Case | Example |
|------|----------|---------|
| **Helm** | Standard Helm charts | grafana, superset, mlflow |
| **K8s Raw Manifest** | CRDs, InfisicalSecret, custom resources | buildkit, arc-runners-raw |
| **Kustomize** | Complex manifests with overlays | percona-operator |

## Common Fields

All apps share these common fields:

```yaml
apps:
  - name: <app-name>           # Required: unique app name
    namespace: <namespace>      # Required: target namespace
    project: dev                # Default: dev (unless specified otherwise)
    syncWave: "<order>"         # Sync order (lower numbers deploy first)
    dependencies:               # Optional: apps that must deploy first
      - dep-app-name
    ignoreDifferences:          # Optional: ignore specific field diffs
      - group: apiextensions.k8s.io
        kind: CustomResourceDefinition
        jsonPointers:
          - /metadata/annotations
```

---

## Type 1: Helm Chart Application

Use for standard Helm chart deployments.

### Basic Template

```yaml
apps:
  - name: <app-name>
    namespace: <namespace>
    project: dev
    syncWave: "10"
    source:
      repoURL: <helm-repo-url>
      chart: <chart-name>
      targetRevision: "<version>"
      helm:
        releaseName: <release-name>
        values: |
          replicaCount: 1

          service:
            type: ClusterIP
            port: <app-port>

          resources:
            requests:
              cpu: <cpu>
              memory: <memory>
            limits:
              cpu: <cpu>
              memory: <memory>
```

### Real Example: Grafana

```yaml
apps:
  - name: grafana
    namespace: monitoring
    project: dev
    syncWave: "10"
    source:
      repoURL: https://grafana.github.io/helm-charts
      chart: grafana
      targetRevision: "7.0.0"
      helm:
        releaseName: grafana
        values: |
          replicas: 1

          service:
            type: ClusterIP
            port: 3000

          persistence:
            enabled: true
            size: 10Gi

          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 1Gi
```

### GPU Workload Template

```yaml
apps:
  - name: <app-name>
    namespace: <namespace>
    project: dev
    syncWave: "10"
    source:
      repoURL: <helm-repo-url>
      chart: <chart-name>
      targetRevision: "<version>"
      helm:
        releaseName: <release-name>
        values: |
          resources:
            requests:
              cpu: "2"
              memory: 8Gi
              nvidia.com/gpu: "1"
            limits:
              cpu: "4"
              memory: 16Gi
              nvidia.com/gpu: "1"

          tolerations:
            - key: nvidia.com/gpu
              operator: Exists
              effect: NoSchedule

          nodeSelector:
            nvidia.com/gpu.present: "true"
```

---

## Type 2: K8s Raw Manifest (Bedag Raw Chart)

Use for CRDs, InfisicalSecret, and custom Kubernetes resources.
**This uses the Bedag raw chart to deploy raw Kubernetes manifests.**

### Template

```yaml
apps:
  - name: <app-name>
    namespace: <namespace>
    project: dev
    syncWave: "<order>"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: <release-name>
        values: |
          resources:
            - apiVersion: <api-version>
              kind: <kind>
              metadata:
                name: <resource-name>
                namespace: <namespace>
              spec:
                # resource spec here
```

### InfisicalSecret Template

```yaml
apps:
  - name: <app-name>-raw
    namespace: <namespace>
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: <app-name>-raw
        values: |
          resources:
            - apiVersion: secrets.infisical.com/v1alpha1
              kind: InfisicalSecret
              metadata:
                name: <app-name>-managed-secrets
                namespace: <namespace>
              spec:
                hostAPI: https://app.infisical.com/api
                authentication:
                  universalAuth:
                    secretsScope:
                      projectSlug: home-lab
                      envSlug: "hme"
                      secretsPath: /<app-name>
                    credentialsRef:
                      secretName: infisical-secrets
                      secretNamespace: infisical
                managedKubeSecretReferences:
                  - secretName: <app-name>-managed-secrets
                    secretNamespace: <namespace>
                    creationPolicy: Owner
```

### Real Example: Buildkit (Multiple Resources)

```yaml
apps:
  - name: buildkit
    namespace: buildkit
    project: dev
    syncWave: "10"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: buildkit
        values: |
          resources:
            - apiVersion: secrets.infisical.com/v1alpha1
              kind: InfisicalSecret
              metadata:
                name: buildkit-managed-secrets
                namespace: buildkit
              spec:
                hostAPI: https://app.infisical.com/api
                authentication:
                  universalAuth:
                    secretsScope:
                      projectSlug: home-lab
                      envSlug: "hme"
                      secretsPath: /buildkit
                    credentialsRef:
                      secretName: infisical-secrets
                      secretNamespace: infisical
                managedKubeSecretReferences:
                  - secretName: buildkit-managed-secrets
                    secretNamespace: buildkit
                    creationPolicy: Owner

            - apiVersion: v1
              kind: ServiceAccount
              metadata:
                name: buildkit
                namespace: buildkit

            - apiVersion: v1
              kind: ConfigMap
              metadata:
                name: buildkitd-config
                namespace: buildkit
              data:
                buildkitd.toml: |
                  # config content here

            - apiVersion: apps/v1
              kind: Deployment
              metadata:
                name: buildkitd
                namespace: buildkit
              spec:
                # deployment spec here

            - apiVersion: v1
              kind: Service
              metadata:
                name: buildkitd
                namespace: buildkit
              spec:
                type: ClusterIP
                selector:
                  app: buildkitd
                ports:
                  - name: buildkit
                    port: 1234
                    targetPort: 1234
```

### HTTPRoute via Raw Chart

```yaml
apps:
  - name: <app-name>-routes
    namespace: <namespace>
    project: dev
    syncWave: "15"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: <app-name>-routes
        values: |
          resources:
            - apiVersion: gateway.networking.k8s.io/v1
              kind: HTTPRoute
              metadata:
                name: <app-name>
                namespace: <namespace>
              spec:
                parentRefs:
                  - name: cilium-gateway
                    namespace: kube-system
                hostnames:
                  - "<app-name>.home.lab"
                rules:
                  - matches:
                      - path:
                          type: PathPrefix
                          value: /
                    backendRefs:
                      - name: <app-name>
                        port: 8080
```

---

## Type 3: Kustomize Application

Use for deploying external CRDs and operators from remote URLs.

### Setup Steps

1. Create kustomization directory: `platform/stacks/kustomize/{app-name}/`
2. Create `kustomization.yaml` inside that directory
3. Reference the kustomize path in your app YAML

### App YAML Template

```yaml
apps:
  - name: <app-name>
    namespace: <namespace>
    project: dev
    syncWave: "10"
    ignoreDifferences:                    # Optional: for CRDs
      - group: apiextensions.k8s.io
        kind: CustomResourceDefinition
        jsonPointers:
          - /metadata/annotations
    source:
      repoURL: https://github.com/ziwon/homelab.git
      targetRevision: main
      path: platform/stacks/kustomize/<app-name>
      kustomize: {}  # Required to recognize as kustomize source
```

### kustomization.yaml Examples

#### Example 1: ClickHouse Operator (Multiple CRDs)

Location: `platform/stacks/kustomize/clickhouse-operator/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - https://raw.githubusercontent.com/Altinity/clickhouse-operator/refs/tags/release-0.25.5/deploy/helm/clickhouse-operator/crds/CustomResourceDefinition-clickhouseinstallations.clickhouse.altinity.com.yaml
  - https://raw.githubusercontent.com/Altinity/clickhouse-operator/refs/tags/release-0.25.5/deploy/helm/clickhouse-operator/crds/CustomResourceDefinition-clickhouseinstallationtemplates.clickhouse.altinity.com.yaml
  - https://raw.githubusercontent.com/Altinity/clickhouse-operator/refs/tags/release-0.25.5/deploy/helm/clickhouse-operator/crds/CustomResourceDefinition-clickhouseoperatorconfigurations.clickhouse.altinity.com.yaml
  - https://raw.githubusercontent.com/Altinity/clickhouse-operator/refs/tags/release-0.25.5/deploy/helm/clickhouse-operator/crds/CustomResourceDefinition-clickhousekeeperinstallations.clickhouse-keeper.altinity.com.yaml
```

#### Example 2: Feast Operator (Single install.yaml)

Location: `platform/stacks/kustomize/feast-operator/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - https://raw.githubusercontent.com/feast-dev/feast/refs/tags/v0.57.0/infra/feast-operator/dist/install.yaml
```

#### Example 3: Percona Operator (Full Stack with Namespace)

Location: `platform/stacks/kustomize/percona-operator/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: postgres
resources:
  - https://raw.githubusercontent.com/percona/percona-postgresql-operator/v2.7.0/deploy/crd.yaml
  - https://raw.githubusercontent.com/percona/percona-postgresql-operator/v2.7.0/deploy/rbac.yaml
  - https://raw.githubusercontent.com/percona/percona-postgresql-operator/v2.7.0/deploy/operator.yaml
```

### When to Use Kustomize

- Installing CRDs from external repos (operators)
- When Helm chart doesn't exist for the operator
- When you need to apply multiple remote YAML files together
- When namespace override is needed across all resources

---

## Combined Pattern: Helm + Raw Resources

When an app needs both Helm chart AND custom resources (like InfisicalSecret), create separate apps with dependencies:

```yaml
apps:
  # Step 1: Deploy secrets first (lower syncWave)
  - name: myapp-raw
    namespace: myapp
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: myapp-raw
        values: |
          resources:
            - apiVersion: secrets.infisical.com/v1alpha1
              kind: InfisicalSecret
              metadata:
                name: myapp-managed-secrets
                namespace: myapp
              spec:
                hostAPI: https://app.infisical.com/api
                authentication:
                  universalAuth:
                    secretsScope:
                      projectSlug: home-lab
                      envSlug: "hme"
                      secretsPath: /myapp
                    credentialsRef:
                      secretName: infisical-secrets
                      secretNamespace: infisical
                managedKubeSecretReferences:
                  - secretName: myapp-managed-secrets
                    secretNamespace: myapp
                    creationPolicy: Owner

  # Step 2: Deploy Helm chart with dependency
  - name: myapp
    namespace: myapp
    project: dev
    syncWave: "10"
    dependencies:
      - myapp-raw
    source:
      repoURL: https://example.github.io/helm-charts
      chart: myapp
      targetRevision: "1.0.0"
      helm:
        releaseName: myapp
        values: |
          secretName: myapp-managed-secrets
          # other values...
```

---

## Important Notes

1. **Project**: Default is `dev` unless explicitly specified otherwise
2. **Namespace**: Prefer using dedicated namespace per app
3. **Resource Limits**: Always set requests/limits for Helm deployments
4. **Secrets**: Never hardcode, always use Infisical via raw chart
5. **Versioning**: Specify exact version in `targetRevision` (no "latest")
6. **syncWave**: Use to control deployment order (lower = earlier)
7. **Bedag Raw Chart**: Always use version `2.0.2` from `https://bedag.github.io/helm-charts`

## Reference

See @.claude/rules/argocd-apps.md for complete templates.
