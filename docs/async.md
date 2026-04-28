# Async API

## Overview

The SDK is async-only. Use `BusinessConnectorClient` inside an asyncio event loop, or
use `AsyncRestTransferClient` directly for low-level REST transfers.

## Installation

```bash
pip install "csob-ceb-business-connector-sdk[async]"
```

## Usage

```python
import asyncio
from pathlib import Path
from csob_ceb_bc import BusinessConnectorClient, CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadFilter

async def main():
    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment.PRODUCTION,
            contract_number="123456",
            client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            certificate=CertificateConfig(
                cert_file=Path("/secure/cert.crt"),
                key_file=Path("/secure/key.key"),
            ),
        )
    )

    result = await client.download_new_files(
        DownloadFilter(file_types=["VYPIS"]),
        Path("/data/inbox"),
    )
    print(f"Downloaded {len(result.downloaded)} files")

asyncio.run(main())
```

## Thread Safety

`BusinessConnectorClient` and `AsyncRestTransferClient` are designed for asyncio event loops.
Do not share instances across threads without an event loop per thread.
