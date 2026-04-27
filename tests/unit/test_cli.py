from unittest.mock import patch, MagicMock

import pytest

from csob_ceb_bc.__main__ import main


def test_cli_no_args_prints_help():
    result = main([])
    assert result == 1


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_download(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.download_new_files.return_value = []
    mock_client_cls.from_config.return_value = mock_client

    result = main([
        "download",
        "--contract", "123456",
        "--guid", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "--cert", "/dev/null",
        "--key", "/dev/null",
        "--types", "VYPIS",
        "--target", "/tmp/inbox",
    ])
    assert result == 0
    mock_client.download_new_files.assert_called_once()


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch.return_value = None
    mock_client_cls.from_config.return_value = mock_client

    result = main([
        "upload",
        "--contract", "123456",
        "--guid", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "--cert", "/dev/null",
        "--key", "/dev/null",
        "--file", "/tmp/pay.xml",
        "--format", "XML SEPA",
        "--mode", "AllOrNothing",
    ])
    assert result == 0
    mock_client.upload_payment_batch.assert_called_once()
