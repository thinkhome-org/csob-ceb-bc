# Configuration

## ConnectorConfig

| Field | Type | Required | Description |
|---|---|---|---|
| `environment` | `Environment` | yes | `PRODUCTION` or `DEMO` |
| `contract_number` | `str` | yes | CEB contract number |
| `client_app_guid` | `str` | yes | Unique application instance GUID |
| `certificate` | `CertificateConfig` | yes | Certificate and key configuration |
| `state_url` | `str` | yes | SQLite database URL |
| `rate_limit` | `RateLimitConfig` | no | Token bucket settings (default: 30 calls / 1200s) |
| `timeouts` | `TimeoutConfig` | no | HTTP timeout overrides |

## CertificateConfig

### PEM/KEY pair

```python
CertificateConfig(
    cert_file=Path("/etc/csob/bccert.crt"),
    key_file=Path("/etc/csob/bccert.key"),
    ca_bundle=None,
)
```

### PFX/P12

```python
CertificateConfig(
    pfx_file=Path("/etc/csob/bccert.pfx"),
    pfx_password_env="CSOB_BC_PFX_PASSWORD",
)
```

The SDK extracts the PEM and key to a temporary directory with `0600` permissions.

## YAML Config File

```yaml
environment: production
contract_number: "TODO"
client_app_guid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
certificate:
  cert_file: "/etc/csob/bccert.crt"
  key_file: "/etc/csob/bccert.key"
state_url: "sqlite:////var/lib/csob-ceb/state.db"
rate_limit:
  soap_calls: 30
  per_seconds: 1200
```

Load with:

```python
from csob_ceb_bc.config import ConnectorConfig
import yaml

with open("config.yaml") as f:
    data = yaml.safe_load(f)
config = ConnectorConfig(**data)
```
