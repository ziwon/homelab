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

### Standard Application Template

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{chart-version}"
    createNamespace: true
    values: |
      # Helm values here
      replicaCount: 1

      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 500m
          memory: 512Mi
```

### Infisical Secret Integration Template

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{chart-version}"
    values: |
      # ... base configuration ...

    # Infisical secret injection
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
                envSlug: prod
                secretsPath: "/{app-name}"
              credentialsRef:
                secretName: infisical-universal-auth
                secretNamespace: infisical
          managedSecretReference:
            secretName: {app-name}-env
            secretNamespace: {target-namespace}
            secretType: Opaque
```

### GPU Workload Template

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{chart-version}"
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

### Dependency Management

```yaml
apps:
  - name: {app-name}
    # ... base configuration ...

    # Sync order control
    syncWave: "10"  # Lower numbers deploy first

    # Dependencies on other apps
    dependencies:
      - name: postgres
        namespace: postgres
      - name: redis
        namespace: redis
```

### Template with HTTPRoute

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    chart: {chart-name}
    repoURL: {helm-repo-url}
    targetRevision: "{chart-version}"
    values: |
      service:
        type: ClusterIP
        port: 8080

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

### Kustomize-based Application

```yaml
apps:
  - name: {app-name}
    namespace: {target-namespace}
    path: platform/stacks/kustomize/{app-name}/overlays/home
    repoURL: git@github.com:ziwon/homelab.git
    targetRevision: main
```

## Important Notes

1. **Namespace**: Prefer using `createNamespace: true`
2. **Resource Limits**: Always set requests/limits
3. **Secrets**: Never hardcode in values, use Infisical
4. **Versioning**: Specify exact version in `targetRevision` (no "latest")
