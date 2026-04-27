# Changelog

## 0.2.0 (2026-04-27)

### Added
- `MetricsCollector` with counters, histograms, gauges and `timed` context manager
- Metrics wired into all workflow managers (download, upload, import protocols)
- `BusinessConnectorClient.metrics_snapshot()` public API
- Edge-case tests: connection timeouts, read timeouts, SSL errors, malformed JSON, malformed schema, expired certificates
- CLI entry point (`python -m csob_ceb_bc`)
- Helper scripts: `convert_pfx_to_pem.py`, `check_certificate.py`
- Documentation: quickstart, configuration, security, troubleshooting

### Changed
- Upload manager tracks `upload_rest_latency_seconds` and `upload_finish_*` counters
- Download manager tracks `download_soap_calls`, `download_latency_seconds`, `download_success`
- Import protocol manager tracks `import_protocol_download_latency_seconds`

## 0.1.0 (2026-04-27)

### Added
- Initial MVP release
- SOAP gateway with zeep (GetDownloadFileList v4, StartUploadFileList v3, FinishUploadFileList v2)
- REST transfer client (streaming GET, multipart POST)
- Certificate store (PEM/KEY/PFX support)
- SQLite state repository with WAL
- Download manager with cursor safety rules
- Upload manager with SHA256 idempotency
- Import protocol polling
- Token bucket rate limiter
- Tenacity-based retry policies
- Structured audit logging with redaction
- Public facade `BusinessConnectorClient`
- Crash recovery (`resume_pending`)
- GitHub Actions CI pipeline
