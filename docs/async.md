# Async REST API

## Overview

For high-throughput or concurrent workloads, use `AsyncRestTransferClient` with `httpx.AsyncClient`.

## Installation

```bash
pip install "csob-ceb-business-connector-sdk[async]"
```

## Usage

```python
import asyncio
from pathlib import Path
from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient

store = CertificateStore(CertificateConfig(
    cert_file=Path("/secure/cert.crt"),
    key_file=Path("/secure/key.key"),
))
client = AsyncRestTransferClient(cert_store=store)

async def main():
    result = await client.download_to_file(
        "https://example.com/file", Path("/data/inbox/file.bin")
    )
    print(f"Downloaded {result.bytes_transferred} bytes")

    upload = await client.upload_multipart(
        "https://example.com/upload", Path("/data/outbox/pay.xml"), "pay.xml"
    )
    print(f"NewFileId: {upload.new_file_id}")

asyncio.run(main())
```

## Differences from Sync Client

| Feature | `RestTransferClient` | `AsyncRestTransferClient` |
|---|---|---|
| HTTP client | `httpx.Client` | `httpx.AsyncClient` |
| Download | `iter_bytes()` | `aiter_bytes()` |
| Upload | `client.post()` | `await client.post()` |
| Retry | `tenacity` sync | `tenacity` async-aware |

## Thread Safety

`AsyncRestTransferClient` is designed for asyncio event loops. Do not share instances across threads without an event loop per thread.
