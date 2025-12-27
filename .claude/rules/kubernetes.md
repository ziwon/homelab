# Kubernetes Working Rules

## Command Rules

### Read-only (Auto-allowed)
```bash
kubectl get <resource>
kubectl describe <resource>
kubectl logs <pod>
kubectl top <node|pod>
```

### Dangerous Commands (Manual confirmation required)
```bash
kubectl delete   # Delete resources
kubectl apply    # Apply resources (may violate GitOps)
kubectl edit     # Direct modification (causes drift)
kubectl exec     # Container access
```

## GitOps Principles

1. **Declarative Management**: All changes through Git
2. **No Manual kubectl apply**: ArgoCD handles synchronization
3. **No Direct Modifications**: Avoid using `kubectl edit`

## Required Fields When Creating Resources

### Pod/Deployment
```yaml
spec:
  containers:
    - name: app
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: 1000m
          memory: 1Gi

      # Health checks required
      livenessProbe:
        httpGet:
          path: /health
          port: 8080
        initialDelaySeconds: 10
        periodSeconds: 10

      readinessProbe:
        httpGet:
          path: /ready
          port: 8080
        initialDelaySeconds: 5
        periodSeconds: 5

      # Security context
      securityContext:
        runAsNonRoot: true
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
```

### Service
```yaml
spec:
  type: ClusterIP  # Use Gateway API instead of LoadBalancer
  ports:
    - name: http   # Port name required
      port: 80
      targetPort: 8080
```

## Namespace Conventions

| Pattern | Purpose |
|---------|---------|
| `argocd` | ArgoCD system |
| `kube-system` | K8s core components |
| `monitoring` | Monitoring stack |
| `{app-name}` | Individual apps (single namespace) |

## Label Standards

```yaml
metadata:
  labels:
    app.kubernetes.io/name: myapp
    app.kubernetes.io/instance: myapp-prod
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: myplatform
    app.kubernetes.io/managed-by: argocd
```

## Debugging Procedure

1. Check Pod status: `kubectl get pods -n <ns>`
2. Check Events: `kubectl describe pod <pod> -n <ns>`
3. Check Logs: `kubectl logs <pod> -n <ns> --tail=100`
4. Previous container logs: `kubectl logs <pod> -n <ns> --previous`
5. ArgoCD status: `argocd app get <app>`
