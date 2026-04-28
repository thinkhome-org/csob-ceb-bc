from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csob_ceb_bc.__main__ import main
from csob_ceb_bc.errors import CsobBCError


def test_cli_no_args_prints_help():
    result = main([])
    assert result == 1


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_download(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    batch_mock = MagicMock()
    batch_mock.downloaded = []
    batch_mock.pending = []
    mock_client.download_new_files = AsyncMock(return_value=batch_mock)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "download",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--types",
            "VYPIS",
            "--target",
            "/tmp/inbox",
        ]
    )
    assert result == 0
    mock_client.download_new_files.assert_called_once()


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch = AsyncMock(return_value=None)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--file",
            "/tmp/pay.xml",
            "--format",
            "XML SEPA",
            "--mode",
            "AllOrNothing",
        ]
    )
    assert result == 0
    mock_client.upload_payment_batch.assert_called_once()


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload_with_result(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    result_mock = MagicMock()
    result_mock.status.value = "I"
    result_mock.ticket_id = "T-123"
    mock_client.upload_payment_batch = AsyncMock(return_value=result_mock)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--file",
            "/tmp/pay.xml",
        ]
    )
    assert result == 0


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_download_with_environment(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    batch_mock = MagicMock()
    batch_mock.downloaded = []
    batch_mock.pending = []
    mock_client.download_new_files = AsyncMock(return_value=batch_mock)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "download",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--environment",
            "demo",
        ]
    )
    assert result == 0
    config = mock_client_cls.from_config.call_args[0][0]
    assert config.environment.value == "demo"


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload_with_state_url(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch = AsyncMock(return_value=None)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--file",
            "/tmp/pay.xml",
            "--state-url",
            "sqlite:///custom.db",
        ]
    )
    assert result == 0
    config = mock_client_cls.from_config.call_args[0][0]
    assert config.state_url == "sqlite:///custom.db"


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_download_error(mock_client_cls: MagicMock):
    mock_client_cls.from_config.side_effect = CsobBCError("connection failed")
    with pytest.raises(CsobBCError):
        main(
            [
                "download",
                "--contract",
                "123456",
                "--guid",
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "--cert",
                "/dev/null",
                "--key",
                "/dev/null",
            ]
        )


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload_error(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch = AsyncMock(side_effect=CsobBCError("upload failed"))
    mock_client_cls.from_config.return_value = mock_client
    with pytest.raises(CsobBCError):
        main(
            [
                "upload",
                "--contract",
                "123456",
                "--guid",
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "--cert",
                "/dev/null",
                "--key",
                "/dev/null",
                "--file",
                "/tmp/pay.xml",
            ]
        )


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_download_with_pfx(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    batch_mock = MagicMock()
    batch_mock.downloaded = []
    batch_mock.pending = []
    mock_client.download_new_files = AsyncMock(return_value=batch_mock)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "download",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--pfx",
            "/dev/null",
            "--pfx-password-env",
            "MY_PFX_PASS",
        ]
    )
    assert result == 0
    config = mock_client_cls.from_config.call_args[0][0]
    assert config.certificate.pfx_file == Path("/dev/null")
    assert config.certificate.pfx_password_env == "MY_PFX_PASS"


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload_with_pfx(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch = AsyncMock(return_value=None)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--pfx",
            "/dev/null",
            "--file",
            "/tmp/pay.xml",
        ]
    )
    assert result == 0
    mock_client.upload_payment_batch.assert_called_once()


def test_cli_missing_cert_args():
    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--file",
            "/tmp/pay.xml",
        ]
    )
    assert result == 1


@patch("csob_ceb_bc.__main__.BusinessConnectorClient")
def test_cli_upload_with_separator_and_skip_duplicates(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client.upload_payment_batch = AsyncMock(return_value=None)
    mock_client_cls.from_config.return_value = mock_client

    result = main(
        [
            "upload",
            "--contract",
            "123456",
            "--guid",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "--cert",
            "/dev/null",
            "--key",
            "/dev/null",
            "--file",
            "/tmp/pay.csv",
            "--format",
            "XML SEPA",
            "--separator",
            ";",
            "--skip-check-duplicates",
        ]
    )
    assert result == 0
    call = mock_client.upload_payment_batch.call_args[1]["metadata"]
    assert call.separator == ";"
    assert call.skip_check_duplicates is True
