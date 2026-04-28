# Quick Start

## Installation

```bash
pip install "csob-ceb-business-connector-sdk[async]"
```

## Minimal Example

```python
import asyncio
from pathlib import Path
from csob_ceb_bc import BusinessConnectorClient, ConnectorConfig, CertificateConfig, Environment
from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadMode

async def main():
    config = ConnectorConfig(
        environment=Environment.PRODUCTION,
        contract_number="YOUR_CONTRACT",
        client_app_guid="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        certificate=CertificateConfig(
            cert_file=Path("/secure/certs/bccert.crt"),
            key_file=Path("/secure/certs/bccert.key"),
        ),
        state_url="sqlite:////var/lib/csob-ceb/state.db",
    )

    client = BusinessConnectorClient.from_config(config)

    files = await client.download_new_files(
        filter=DownloadFilter(file_types=["VYPIS"]),
        target_dir=Path("/data/inbox"),
    )
    print(f"Downloaded {len(files)} files")

    result = await client.upload_payment_batch(
        file=Path("/data/outbox/payments.xml"),
        metadata=UploadFile(
            filename="payments.xml",
            format="XML SEPA",
            mode=UploadMode.AllOrNothing,
        ),
    )
    if result:
        print(f"Upload started: {result.status}")

    print(client.metrics_snapshot())

asyncio.run(main())
```

## Environment Variables

All config fields can be overridden via environment variables prefixed with `CSOB_BC_`:

```bash
export CSOB_BC_CONTRACT_NUMBER=YOUR_CONTRACT
export CSOB_BC_CLIENT_APP_GUID=xxx
export CSOB_BC_CERTIFICATE__CERT_FILE=/secure/certs/bccert.crt
export CSOB_BC_CERTIFICATE__KEY_FILE=/secure/certs/bccert.key
export CSOB_BC_STATE_URL=sqlite:////var/lib/csob-ceb/state.db
```
