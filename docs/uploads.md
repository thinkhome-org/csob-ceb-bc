# Upload Workflow

## Overview

The upload manager handles the full lifecycle: SHA256 hash, idempotency check, SOAP start, REST multipart POST, SOAP finish.

## Stages

1. Compute SHA256
2. Check idempotency (skip if already uploaded)
3. `StartUploadFileList v3`
4. If status `U`: multipart POST
5. Store `NewFileId`
6. `FinishUploadFileList v2`
7. If status `I`: import started

## Idempotency

Uploads are deduplicated by SHA256 hash. Once an upload finishes with `I` or `R`, it is never retried automatically.

## Crash Recovery

If the process crashes after REST upload but before finish:

```python
await client.resume_pending()
```

This resumes all uploads with `NewFileId` stored but not finished.

## Modes

| Mode | Description |
|---|---|
| `IncludeIncorrect` | Import correct records, report incorrect |
| `OnlyCorrect` | Import only correct records |
| `AllOrNothing` | Rollback entire batch on any error |
| `SignedAllOrNothing` | CAdES-BES signed batch; duplicate check cannot be skipped |

## REST Multipart Upload

The SDK uses `multipart/form-data` with the file field named `fileupload` and
`Content-Type: application/octet-stream` per the ČSOB manual.

> **Note on `Content-Disposition`**
> The implementation guide contains two different formulations:
> - Example request: `Content-Disposition: form-data; name="fileupload"; filename="..."`
> - MIME header table: `Content-Disposition: attachment; filename="..."`
>
> The SDK relies on the HTTP client library (httpx) to generate the multipart
> payload, which produces the standard `form-data` variant. This matches the
> example request in the manual and conforms to RFC 2046.

## Metrics

- `upload_start_calls` — counter
- `upload_rest_success` — counter
- `upload_rest_latency_seconds` — histogram
- `upload_finish_calls` — counter
- `upload_finish_import_started` — counter
- `upload_finish_rejected` — counter
- `upload_idempotent_skips` — counter
- `upload_resume_success` — counter
- `upload_pending_count` — gauge
