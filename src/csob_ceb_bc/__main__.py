"""CLI entry point for ČSOB CEB Business Connector SDK."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from csob_ceb_bc import BusinessConnectorClient, CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadFilter


def _certificate_config(args: argparse.Namespace) -> CertificateConfig:
    if args.pfx:
        return CertificateConfig(
            pfx_file=Path(args.pfx),
            pfx_password_env=args.pfx_password_env,
        )
    return CertificateConfig(
        cert_file=Path(args.cert),
        key_file=Path(args.key),
    )


def cmd_download(args: argparse.Namespace) -> int:
    client = BusinessConnectorClient.from_config(
        ConnectorConfig(
            environment=Environment(args.environment),
            contract_number=args.contract,
            client_app_guid=args.guid,
            certificate=_certificate_config(args),
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
            certificate=_certificate_config(args),
            state_url=args.state_url,
        )
    )
    upload_kwargs = {
        "filename": Path(args.file).name,
        "format": args.format,
        "mode": UploadMode(args.mode),
    }
    if args.separator is not None:
        upload_kwargs["separator"] = args.separator
    if args.skip_check_duplicates:
        upload_kwargs["skip_check_duplicates"] = True
    result = client.upload_payment_batch(
        file=Path(args.file),
        metadata=UploadFile(**upload_kwargs),
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
    dl.add_argument("--cert", default="")
    dl.add_argument("--key", default="")
    dl.add_argument("--pfx", default="")
    dl.add_argument("--pfx-password-env", default="CSOB_BC_PFX_PASSWORD")
    dl.add_argument("--types", default="VYPIS,AVIZO")
    dl.add_argument("--target", default="./inbox")
    dl.add_argument("--environment", default="production")
    dl.add_argument("--state-url", default="sqlite:///csob_ceb_state.db")
    dl.set_defaults(func=cmd_download)

    up = subparsers.add_parser("upload", help="Upload payment batch")
    up.add_argument("--contract", required=True)
    up.add_argument("--guid", required=True)
    up.add_argument("--cert", default="")
    up.add_argument("--key", default="")
    up.add_argument("--pfx", default="")
    up.add_argument("--pfx-password-env", default="CSOB_BC_PFX_PASSWORD")
    up.add_argument("--file", required=True)
    up.add_argument("--format", default="XML SEPA")
    up.add_argument("--mode", default="AllOrNothing")
    up.add_argument("--separator", default=None)
    up.add_argument("--skip-check-duplicates", action="store_true", default=False)
    up.add_argument("--environment", default="production")
    up.add_argument("--state-url", default="sqlite:///csob_ceb_state.db")
    up.set_defaults(func=cmd_upload)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    if not args.pfx and not (args.cert and args.key):
        print("Error: either --pfx or both --cert and --key are required", file=sys.stderr)
        return 1
    return args.func(args)  # type: ignore[no-any-return]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
