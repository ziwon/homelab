---
name: argocd-generator
description: Generates ArgoCD Application manifests following the App-of-Apps pattern.
---

# ArgoCD Application Generator

## YAML RULES (CRITICAL)
- Each key MUST appear EXACTLY ONCE in its parent map
- NEVER repeat configuration blocks
- Keep values MINIMAL - only necessary overrides

## File Location
```
platform/stacks/{NN}-{category}/overlays/home/{app-name}.yaml
```

## Stack Categories
| Stack | Path | Purpose |
|-------|------|---------|
| 00-core | Core infra | cert-manager, cloudflared |
| 01-platforms | Platform services | argo-workflows, harbor |
| 02-o11y | Observability | grafana, tempo |
| 03-data | Databases | postgres, redis |
| 04-ml | ML services | feast, ray, mlflow |
| 05-workloads | Applications | |
| 06-labs | Experimental | |

## Type 1: Helm Chart

```yaml
apps:
  - name: myapp
    namespace: myapp
    project: dev
    syncWave: "10"
    source:
      repoURL: https://charts.example.io
      chart: myapp
      targetRevision: "1.0.0"
      helm:
        releaseName: myapp
        values: |
          replicaCount: 1
          postgresql:
            enabled: false
          redis:
            enabled: false
          persistence:
            enabled: true
            size: 10Gi
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
```

## Type 2: Raw Manifest (InfisicalSecret)

```yaml
apps:
  - name: myapp-raw
    namespace: myapp
    project: dev
    syncWave: "5"
    source:
      repoURL: https://bedag.github.io/helm-charts
      chart: raw
      targetRevision: "2.0.2"
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
```

## Combined Pattern (Secrets + Helm)

Put both in ONE file with dependencies:

```yaml
apps:
  - name: myapp-raw
    namespace: myapp
    syncWave: "5"
    source:
      # InfisicalSecret via raw chart...

  - name: myapp
    namespace: myapp
    syncWave: "10"
    dependencies:
      - myapp-raw
    source:
      # Helm chart...
```

## Notes
- project: always `dev`
- syncWave: lower = earlier (5 for secrets, 10 for apps)
- Bedag raw chart: version `2.0.2`
