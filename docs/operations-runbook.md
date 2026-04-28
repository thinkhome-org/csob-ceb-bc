# Operations Runbook

## Daily Checks

1. Review `metrics_snapshot()` for anomalies
2. Check certificate expiry (`cert_days_left` gauge)
3. Verify no pending uploads (`upload_pending_count`)
4. Check for rate limit errors (`CsobBCRateLimitError`)

## Weekly Checks

1. Review disk space for state database and download directories
2. Check logs for permanent errors (SOAP 1002, 1011, 1012)
3. Validate backup of PFX/certificates including private keys

## Incident Response

| Symptom | Likely Cause | Action |
|---|---|---|
| SOAP 1101 | Rate limit | Increase polling interval, check for parallel clients |
| SOAP 1011 | Certificate not registered | Register in CEB portal |
| SOAP 1012 | Certificate blocked | Security incident, contact bank |
| HTTP 400/404 | URL expired | File >15 days old, no recovery |
| Upload R | Duplicate or invalid | Check hash, format, filename |
| High pending | Crash or network issue | Run `await client.resume_pending()` |

## Certificate Renewal

1. Generate new CSR or request new certificate
2. Register in CEB portal
3. Update SDK config with new cert/key
4. Verify with `check_certificate.py` script
5. Monitor for 24h

## Backup

- State database: daily backup
- Certificates: encrypted backup of full PFX or PEM+KEY
- Config files: version controlled (without secrets)
