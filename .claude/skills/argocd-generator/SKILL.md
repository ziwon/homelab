---
name: argocd-generator
description: Generates ArgoCD Application manifests following the App-of-Apps pattern. Use when creating new applications, deploying services, or adding apps to the homelab platform.
---

# ArgoCD Application Generator

Generate ArgoCD applications following the App-of-Apps pattern.

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

## Standard Template

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{version}"
    createNamespace: true
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
