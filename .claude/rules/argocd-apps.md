# ArgoCD Application Template Rules

## App-of-Apps Pattern

This project follows the App-of-Apps pattern using ApplicationSet.

### Adding a New Application

1. Create a YAML file in the appropriate stack directory:
   - `platform/stacks/00-core/overlays/home/` - Core infrastructure
   - `platform/stacks/01-platforms/overlays/home/` - Platform services
   - `platform/stacks/02-o11y/overlays/home/` - Monitoring
   - `platform/stacks/03-data/overlays/home/` - Databases
   - `platform/stacks/04-ml/overlays/home/` - ML services
   - `platform/stacks/05-workloads/overlays/home/` - Applications
   - `platform/stacks/06-labs/overlays/home/` - Experimental services

2. Filename: `{app-name}.yaml`

## Application Source Types

This project supports 3 types of application sources:

| Type | Use Case | Example |
|------|----------|---------|
| **Helm** | Standard Helm charts | grafana, superset |
| **K8s Raw Manifest** | CRDs, InfisicalSecret, HTTPRoute | buildkit, arc-runners-raw |
| **Kustomize** | Complex manifests with overlays | percona-operator |

## Common Fields

```yaml
apps:
  - name: <app-name>           # Required
    namespace: <namespace>      # Required
    project: dev                # Default: dev
    syncWave: "<order>"         # Lower = deploys first
    dependencies:               # Optional
      - dep-app-name
```

---

## Type 1: Helm Chart Application

```yaml
apps:
  - name: {app-name}
    namespace: {namespace}
    project: dev
    syncWave: "10"
    source:
      repoURL: {helm-repo-url}
      chart: {chart-name}
      targetRevision: "{version}"
      helm:
        releaseName: {release-name}
        values: |
          replicaCount: 1

          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

### GPU Workload Template

```yaml
apps:
  - name: {app-name}
    namespace: {namespace}
    project: dev
    syncWave: "10"
    source:
      repoURL: {helm-repo-url}
      chart: {chart-name}
      targetRevision: "{version}"
      helm:
        releaseName: {release-name}
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

Use for CRDs, InfisicalSecret, HTTPRoute, and any custom Kubernetes resources.

### Basic Template

```yaml
apps:
  - name: {app-name}-raw
    namespace: {namespace}
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: {app-name}-raw
        values: |
          resources:
            - apiVersion: <api-version>
              kind: <kind>
              metadata:
                name: <resource-name>
                namespace: {namespace}
              spec:
                # resource spec here
```

### InfisicalSecret Template

```yaml
apps:
  - name: {app-name}-raw
    namespace: {namespace}
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: {app-name}-raw
        values: |
          resources:
            - apiVersion: secrets.infisical.com/v1alpha1
              kind: InfisicalSecret
              metadata:
                name: {app-name}-managed-secrets
                namespace: {namespace}
              spec:
                hostAPI: https://app.infisical.com/api
                authentication:
                  universalAuth:
                    secretsScope:
                      projectSlug: home-lab
                      envSlug: "hme"
                      secretsPath: /{app-name}
                    credentialsRef:
                      secretName: infisical-secrets
                      secretNamespace: infisical
                managedKubeSecretReferences:
                  - secretName: managed-{app-name}-secrets
                    secretNamespace: {namespace}
                    creationPolicy: Owner
```

### HTTPRoute Template

```yaml
apps:
  - name: {app-name}-raw
    namespace: {namespace}
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: {app-name}-raw
        values: |
          resources:
            - apiVersion: gateway.networking.k8s.io/v1
              kind: HTTPRoute
              metadata:
                name: {app-name}
                namespace: {namespace}
              spec:
                parentRefs:
                  - name: cilium
                    namespace: infra
                    sectionName: https-private
                hostnames:
                  - "{app-name}.home.lab"
                rules:
                  - matches:
                      - path:
                          type: PathPrefix
                          value: /
                    backendRefs:
                      - name: {app-name}
                        port: 8080
```

### Combined: InfisicalSecret + HTTPRoute

```yaml
apps:
  - name: {app-name}-raw
    namespace: {namespace}
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: 2.0.2
      helm:
        releaseName: {app-name}-raw
        values: |
          resources:
            - apiVersion: secrets.infisical.com/v1alpha1
              kind: InfisicalSecret
              metadata:
                name: {app-name}-managed-secrets
                namespace: {namespace}
              spec:
                hostAPI: https://app.infisical.com/api
                authentication:
                  universalAuth:
                    secretsScope:
                      projectSlug: home-lab
                      envSlug: "hme"
                      secretsPath: /{app-name}
                    credentialsRef:
                      secretName: infisical-secrets
                      secretNamespace: infisical
                managedKubeSecretReferences:
                  - secretName: {app-name}-managed-secrets
                    secretNamespace: {namespace}
                    creationPolicy: Owner

            - apiVersion: gateway.networking.k8s.io/v1
              kind: HTTPRoute
              metadata:
                name: {app-name}
                namespace: {namespace}
              spec:
                parentRefs:
                  - name: cilium
                    namespace: infra
                    sectionName: https-private
                hostnames:
                  - "{app-name}.home.lab"
                rules:
                  - matches:
                      - path:
                          type: PathPrefix
                          value: /
                    backendRefs:
                      - name: {app-name}
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
  - name: {app-name}
    namespace: {namespace}
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
      path: platform/stacks/kustomize/{app-name}
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

When an app needs both Helm chart AND custom resources, use dependencies:

```yaml
apps:
  # Step 1: Raw resources first (lower syncWave)
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
              # ... InfisicalSecret spec ...

            - apiVersion: gateway.networking.k8s.io/v1
              kind: HTTPRoute
              # ... HTTPRoute spec ...

  # Step 2: Helm chart with dependency
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

1. **Project**: Default is `dev` unless explicitly specified
2. **Namespace**: Use dedicated namespace per app
3. **Resource Limits**: Always set requests/limits for Helm deployments
4. **Secrets**: Never hardcode, always use Infisical via raw chart
5. **Versioning**: Specify exact version in `targetRevision` (no "latest")
6. **Bedag Raw Chart**: Always use version `2.0.2`
7. **syncWave**: Use to control deployment order (lower = earlier)
8. **Dependencies**: List app names only (not name/namespace objects)
