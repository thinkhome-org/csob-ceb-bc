from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadMode
from csob_ceb_bc.soap.async_gateway import AsyncSoapGateway


@pytest.mark.asyncio
async def test_async_gateway_delegates_download_call():
    gateway = MagicMock()
    expected = MagicMock()
    gateway.get_download_file_list_v4.return_value = expected
    async_gateway = AsyncSoapGateway(gateway)

    result = await async_gateway.get_download_file_list_v4(
        prev_query_timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        filter=DownloadFilter(file_types=["VYPIS"]),
    )

    assert result is expected
    gateway.get_download_file_list_v4.assert_called_once()


@pytest.mark.asyncio
async def test_async_gateway_delegates_upload_calls():
    gateway = MagicMock()
    gateway.start_upload_file_list_v3.return_value = ["start"]
    gateway.finish_upload_file_list_v2.return_value = ["finish"]
    async_gateway = AsyncSoapGateway(gateway)

    upload_file = UploadFile(
        filename="pay.xml",
        format="XML SEPA",
        mode=UploadMode.AllOrNothing,
        hash="a" * 64,
        size=42,
    )

    start_result = await async_gateway.start_upload_file_list_v3([upload_file])
    finish_result = await async_gateway.finish_upload_file_list_v2(
        [("pay.xml", "a" * 64, "NFID-1")]
    )

    assert start_result == ["start"]
    assert finish_result == ["finish"]
