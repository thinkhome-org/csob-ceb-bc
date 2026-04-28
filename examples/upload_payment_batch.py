import asyncio
from pathlib import Path

from csob_ceb_bc import (
    BusinessConnectorClient,
    CertificateConfig,
    ConnectorConfig,
    Environment,
)
from csob_ceb_bc.models import UploadFile, UploadMode


async def main() -> None:
    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment.DEMO,
            contract_number="123456",
            client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            certificate=CertificateConfig(cert_file=Path("demo.crt"), key_file=Path("demo.key")),
        )
    )

    result = await client.upload_payment_batch(
        file=Path("payments.xml"),
        metadata=UploadFile(
            filename="payments.xml",
            format="XML SEPA",
            mode=UploadMode.AllOrNothing,
        ),
    )
    print(result)


asyncio.run(main())
