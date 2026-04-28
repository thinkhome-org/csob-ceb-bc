import asyncio
from pathlib import Path

from csob_ceb_bc import (
    BusinessConnectorClient,
    CertificateConfig,
    ConnectorConfig,
    Environment,
)
from csob_ceb_bc.models import DownloadFilter


async def main() -> None:
    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment.DEMO,
            contract_number="123456",
            client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            certificate=CertificateConfig(cert_file=Path("demo.crt"), key_file=Path("demo.key")),
        )
    )

    while True:
        await client.resume_pending()
        await client.download_new_files(
            DownloadFilter(file_types=["VYPIS", "AVIZO"]),
            Path("./inbox"),
        )
        await client.poll_import_protocols()
        await asyncio.sleep(60)


asyncio.run(main())
