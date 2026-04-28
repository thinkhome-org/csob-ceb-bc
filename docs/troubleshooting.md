# Troubleshooting

## Common Errors

### `CsobBCCertificateError: Certificate expires in N days`

Renew the certificate before expiry. The SDK checks at startup.

### `CsobBCRateLimitError`

Too many SOAP calls. Wait for the protective interval (default 20 min).

### `CsobBCSoapFault` with code 1002

Contract does not have Business Connector enabled. Contact ČSOB.

### `CsobBCSoapFault` with code 1011

Certificate not registered or contract inactive. Register in CEB portal.

### `CsobBCHttpError: HTTP 400`

REST URL expired (download older than 15 days) or invalid upload parameters.

### Upload rejected with status R

File may already have been imported, or format is invalid. Check logs for `ticket_id`.

## Crash Recovery

If the process crashes mid-upload:

```python
await client.resume_pending()
```

This finds uploads with `NewFileId` stored but not finished, and calls `FinishUploadFileList`.

## Metrics

Inspect runtime metrics:

```python
print(client.metrics_snapshot())
```
