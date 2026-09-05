# DeepFX ingestion schema

Vendored from restack/deepfx commit `9fcb3fb56dd01f04c309a0fcd9d07c65e81caa62`,
`deploy/clickhouse/bootstrap`. Argo CD already has access to this infrastructure
repository; it does not have credentials for the private DeepFX HTTPS repository.
Keep these manifests synchronized with the source generator and tests.

The PostSync job only creates absent schema objects. The read-only CronJob checks
consumer presence, recent polling and recent exceptions every five minutes.
Neither job changes ClickHouse server configuration or restarts application pods.
Job failures are visible in Kubernetes; external notification routing is separate.
