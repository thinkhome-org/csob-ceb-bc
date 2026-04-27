# Download Workflow

## Overview

The download manager fetches files via SOAP `GetDownloadFileList v4` and REST streaming GET.

## Cursor Safety

The SDK **never** advances `PrevQueryTimestamp` if:
- Any file has status `R` (preparing)
- Any file is missing a `Url`

This prevents missing files that are still being prepared by the bank.

## File Statuses

| Status | Meaning | Action |
|---|---|---|
| `R` | Preparing | Skip, do not advance cursor |
| `D` | Ready | Download via REST URL |
| `F` | Permanent failure | Log and skip |

## Usage

```python
from csob_ceb_bc.models import DownloadFilter, DownloadFileType

files = client.download_new_files(
    filter=DownloadFilter(file_types=["VYPIS", "AVIZO"]),
    target_dir=Path("/data/inbox"),
)
```

## Atomic Writes

Files are streamed to `*.part` and renamed atomically on success.

## Metrics

- `download_soap_calls` — counter
- `download_file_count` — gauge per batch
- `download_latency_seconds` — histogram
- `download_success` — counter
- `download_unresolved_files` — counter
