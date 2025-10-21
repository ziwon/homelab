#!/bin/bash

VERSION="${1:-1.2.0}"

# Install Gateway API CRDs
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/standard/gateway.networking.k8s.io_gatewayclasses.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/standard/gateway.networking.k8s.io_gateways.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/standard/gateway.networking.k8s.io_httproutes.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/standard/gateway.networking.k8s.io_referencegrants.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/standard/gateway.networking.k8s.io_grpcroutes.yaml

# Install experimental TLSRoute CRD
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v${VERSION}/config/crd/experimental/gateway.networking.k8s.io_tlsroutes.yaml