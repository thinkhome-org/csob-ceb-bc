# Changelog

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
