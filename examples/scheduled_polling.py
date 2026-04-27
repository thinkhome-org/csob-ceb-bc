import time
from pathlib import Path
from csob_ceb_bc import BusinessConnectorClient, ConnectorConfig, CertificateConfig, Environment
from csob_ceb_bc.models import DownloadFilter

client = BusinessConnectorClient.from_config(
    ConnectorConfig(
        environment=Environment.DEMO,
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(cert_file=Path("demo.crt"), key_file=Path("demo.key")),
    )
)

while True:
    client.resume_pending()
    client.download_new_files(DownloadFilter(file_types=["VYPIS", "AVIZO"]), Path("./inbox"))
    client.poll_import_protocols()
    time.sleep(60)
