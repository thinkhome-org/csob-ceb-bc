# Security

## Certificate Handling

- Private keys must have `0400` or `0600` permissions.
- Never commit keys or PFX files to version control.
- Use environment variables or a secret manager for PFX passwords.
- The SDK validates certificate expiry on startup (default: minimum 7 days).

## Logging and Redaction

- Contract numbers are redacted in logs (e.g., `123***`).
- REST URL query tokens are redacted.
- File contents are never logged.
- SHA256 hashes are safe to log.

## Rate Limiting

The SDK enforces a token-bucket rate limiter to respect ČSOB's protective interval:
- Default: 30 SOAP calls per 1200 seconds (20 minutes).
- Exceeding the limit raises `CsobBCRateLimitError`.
