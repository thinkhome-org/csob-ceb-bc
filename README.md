# ČSOB CEB Business Connector SDK

Python SDK for automated file download and upload via ČSOB CEB Business Connector.

## Installation

```bash
pip install csob-ceb-business-connector-sdk
```

## Quickstart

```python
from pathlib import Path
from csob_ceb_bc import BusinessConnectorClient, ConnectorConfig, CertificateConfig, Environment
from csob_ceb_bc.models import DownloadFilter

client = BusinessConnectorClient.from_config(
    ConnectorConfig(
        environment=Environment.PRODUCTION,
        contract_number="YOUR_CONTRACT",
        client_app_guid="your-guid",
        certificate=CertificateConfig(
            cert_file=Path("/secure/cert.crt"),
            key_file=Path("/secure/key.key"),
        ),
    )
)

files = client.download_new_files(
    filter=DownloadFilter(file_types=["VYPIS", "AVIZO"]),
    target_dir=Path("./inbox"),
)
```

## Documentation

See `examples/` and `docs/` for detailed guides.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
