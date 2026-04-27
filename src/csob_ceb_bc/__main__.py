"""CLI entry point for ČSOB CEB Business Connector SDK."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from csob_ceb_bc import BusinessConnectorClient, CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadFilter


def cmd_download(args: argparse.Namespace) -> int:
    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment(args.environment),
            contract_number=args.contract,
            client_app_guid=args.guid,
            certificate=CertificateConfig(
                cert_file=Path(args.cert),
                key_file=Path(args.key),
            ),
            state_url=args.state_url,
        )
    )
    files = client.download_new_files(
        filter=DownloadFilter(file_types=args.types.split(",")),
        target_dir=Path(args.target),
    )
    print(f"Downloaded {len(files)} files")
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    from csob_ceb_bc.models import UploadFile, UploadMode

    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment(args.environment),
            contract_number=args.contract,
            client_app_guid=args.guid,
            certificate=CertificateConfig(
                cert_file=Path(args.cert),
                key_file=Path(args.key),
            ),
            state_url=args.state_url,
        )
    )
    result = client.upload_payment_batch(
        file=Path(args.file),
        metadata=UploadFile(
            filename=Path(args.file).name,
            format=args.format,
            mode=UploadMode(args.mode),
        ),
    )
    if result:
        print(f"Upload finished: status={result.status.value}, ticket_id={result.ticket_id}")
    else:
        print("Upload rejected or duplicate")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="csob_ceb_bc")
    subparsers = parser.add_subparsers(dest="command")

    dl = subparsers.add_parser("download", help="Download files")
    dl.add_argument("--contract", required=True)
    dl.add_argument("--guid", required=True)
    dl.add_argument("--cert", required=True)
    dl.add_argument("--key", required=True)
    dl.add_argument("--types", default="VYPIS,AVIZO")
    dl.add_argument("--target", default="./inbox")
    dl.add_argument("--environment", default="production")
    dl.add_argument("--state-url", default="sqlite:///csob_ceb_state.db")
    dl.set_defaults(func=cmd_download)

    up = subparsers.add_parser("upload", help="Upload payment batch")
    up.add_argument("--contract", required=True)
    up.add_argument("--guid", required=True)
    up.add_argument("--cert", required=True)
    up.add_argument("--key", required=True)
    up.add_argument("--file", required=True)
    up.add_argument("--format", default="XML SEPA")
    up.add_argument("--mode", default="AllOrNothing")
    up.add_argument("--environment", default="production")
    up.add_argument("--state-url", default="sqlite:///csob_ceb_state.db")
    up.set_defaults(func=cmd_upload)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)  # type: ignore[no-any-return]


if __name__ == "__main__":
    sys.exit(main())
