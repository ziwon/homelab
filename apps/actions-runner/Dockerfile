FROM docker:29-cli AS docker-cli

FROM ghcr.io/actions/actions-runner:2.336.0

ARG BUILDKIT_VERSION=0.29.0
ARG BUILDX_VERSION=0.33.0

USER root

# Install additional packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      jq \
      unzip && \
    rm -rf /var/lib/apt/lists/*

# Docker CLI
COPY --from=docker-cli /usr/local/bin/docker /usr/bin/docker

# Docker BuildX plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -fsSL "https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}/buildx-v${BUILDX_VERSION}.linux-amd64" \
      -o /usr/local/lib/docker/cli-plugins/docker-buildx && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# BuildKit client (buildctl only)
RUN curl -fsSL "https://github.com/moby/buildkit/releases/download/v${BUILDKIT_VERSION}/buildkit-v${BUILDKIT_VERSION}.linux-amd64.tar.gz" | \
    tar -xz -C /usr/local bin/buildctl && \
    chmod +x /usr/local/bin/buildctl

# Harbor CA certificate
COPY homelab-ca.crt /usr/local/share/ca-certificates/homelab-ca.crt
RUN update-ca-certificates

USER runner
