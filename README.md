# ČSOB CEB Business Connector SDK

Production-ready Python SDK for automated file download and upload via ČSOB CEB Business Connector.

## Features

- **SOAP orchestration**: `GetDownloadFileList v4`, `StartUploadFileList v3`, `FinishUploadFileList v2`
- **REST transfer**: Streaming download, multipart upload
- **mTLS**: Certificate validation, PEM/KEY/PFX support
- **Stateful idempotency**: SQLite persistence with WAL, crash recovery
- **Rate limiting**: Token bucket per contract/certificate
- **Retry policies**: Exponential backoff + jitter via tenacity
- **Audit logging**: Structured JSON logs with redaction

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
        state_url="sqlite:////var/lib/csob-ceb/state.db",
    )
)

# Download new files
files = client.download_new_files(
    filter=DownloadFilter(file_types=["VYPIS", "AVIZO"]),
    target_dir=Path("./inbox"),
)

# Upload payment batch
from csob_ceb_bc.models import UploadFile, UploadMode
result = client.upload_payment_batch(
    file=Path("payments.xml"),
    metadata=UploadFile(filename="payments.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
)

# Poll for import protocols
client.poll_import_protocols()

# Resume after crash
client.resume_pending()
```

## Configuration

Environment variables (prefix `CSOB_BC_`):

```bash
CSOB_BC_CONTRACT_NUMBER=123456
CSOB_BC_ENVIRONMENT=production
CSOB_BC_CLIENT_APP_GUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

YAML config:

```yaml
environment: production
contract_number: "123456"
client_app_guid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
certificate:
  cert_file: "/etc/csob/cert.crt"
  key_file: "/etc/csob/key.key"
state_url: "sqlite:////var/lib/csob-ceb/state.db"
```

## Security

- Private keys must have permissions `400` or `600`
- Certificate expiry is checked at startup
- Logs redact contract numbers and sensitive URL parameters
- Bank file contents are never logged
- `verify=False` is never used

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format .
mypy src
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| SOAP 1101 | Rate limit exceeded | Increase polling interval, check parallel clients |
| SOAP 1011 | Certificate not registered | Register certificate in CEB portal |
| SOAP 1012 | Certificate blocked | Security incident, contact bank |
| HTTP 400/404 | Download URL expired | File older than 15 days, no recovery possible |
| Upload rejected (R) | Duplicate or invalid file | Check hash, format, filename length |

## License

MIT
