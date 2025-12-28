---
name: argocd-generator
description: Generates ArgoCD Application manifests following the App-of-Apps pattern. Use when creating new applications, deploying services, or adding apps to the homelab platform.
---

# ArgoCD Application Generator

Generate ArgoCD applications following the App-of-Apps pattern.

## IMPORTANT: How to Use This Template

1. Extract values from the issue:
   - `helm repo add NAME URL` -> use URL as repoURL
   - Chart version mentioned -> use as targetRevision
   - Any custom values mentioned -> add to values section

2. Fill in ALL fields - never leave placeholders like `{app-name}`

3. The `values:` section must contain actual Helm values for the chart

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

```
platform/stacks/{NN}-{category}/overlays/home/{app-name}.yaml
```

## Real Example: Superset

If issue says: `helm repo add superset http://apache.github.io/superset/`

Create file: `platform/stacks/06-labs/overlays/home/superset.yaml`

```yaml
apps:
  - name: superset
    namespace: superset
    chart: superset
    repoURL: http://apache.github.io/superset
    targetRevision: "0.15.0"
    createNamespace: true
    values: |
      replicaCount: 1

      image:
        repository: apache/superset
        tag: latest

      service:
        type: ClusterIP
        port: 8088

      resources:
        requests:
          cpu: 500m
          memory: 1Gi
        limits:
          cpu: 2000m
          memory: 4Gi

      postgresql:
        enabled: true

      redis:
        enabled: true
```

## Real Example: Grafana

If issue says: `helm repo add grafana https://grafana.github.io/helm-charts`

Create file: `platform/stacks/02-o11y/overlays/home/grafana.yaml`

```yaml
apps:
  - name: grafana
    namespace: monitoring
    chart: grafana
    repoURL: https://grafana.github.io/helm-charts
    targetRevision: "7.0.0"
    createNamespace: true
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

      adminUser: admin
      adminPassword: admin
```

## Template Structure (fill in all values)

```yaml
apps:
  - name: <actual-app-name>
    namespace: <actual-namespace>
    chart: <actual-chart-name>
    repoURL: <actual-helm-repo-url>
    targetRevision: "<actual-version>"
    createNamespace: true
    values: |
      # Add actual Helm values here based on the chart
      replicaCount: 1

      service:
        type: ClusterIP
        port: <app-port>

      resources:
        requests:
          cpu: <appropriate-cpu>
          memory: <appropriate-memory>
        limits:
          cpu: <appropriate-cpu>
          memory: <appropriate-memory>
```

## With Infisical Secrets

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{version}"
    values: |
      # base config here

    extraResources:
      - apiVersion: secrets.infisical.com/v1alpha1
        kind: InfisicalSecret
        metadata:
          name: {app-name}-secrets
        spec:
          hostAPI: https://app.infisical.com/api
          resyncInterval: 60
          authentication:
            universalAuth:
              secretsScope:
                projectSlug: homelab
                envSlug: hme
                secretsPath: "/{app-name}"
              credentialsRef:
                secretName: infisical-universal-auth
                secretNamespace: infisical
          managedSecretReference:
            secretName: {app-name}-env
            secretNamespace: {target-namespace}
            secretType: Opaque
```

## With HTTPRoute (Gateway API)

```yaml
apps:
  - name: {app-name}
    # ... base config ...

    extraResources:
      - apiVersion: gateway.networking.k8s.io/v1
        kind: HTTPRoute
        metadata:
          name: {app-name}
        spec:
          parentRefs:
            - name: cilium-gateway
              namespace: kube-system
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

## GPU Workload Template

```yaml
apps:
  - name: {app-name}
    # ... base config ...
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

## Reference

See @.claude/rules/argocd-apps.md for complete templates.
