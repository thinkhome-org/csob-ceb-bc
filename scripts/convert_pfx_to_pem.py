#!/usr/bin/env python3
"""Convert PFX/P12 certificate to PEM + KEY files."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


def convert(pfx_path: Path, password: bytes | None, out_dir: Path) -> None:
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    private_key, cert, _ = pkcs12.load_key_and_certificates(
        pfx_data, password, default_backend()
    )

    if private_key is None or cert is None:
        print("ERROR: PFX does not contain private key or certificate", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    cert_path = out_dir / "cert.pem"
    key_path = out_dir / "key.pem"

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)

    print(f"Written: {cert_path}")
    print(f"Written: {key_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert PFX/P12 to PEM + KEY")
    parser.add_argument("pfx", type=Path, help="Path to PFX/P12 file")
    parser.add_argument("--password", default=None, help="PFX password (or use PFX_PASSWORD env)")
    parser.add_argument("--out-dir", type=Path, default=Path("."), help="Output directory")
    args = parser.parse_args()

    password = (args.password or os.environ.get("PFX_PASSWORD", "")).encode() or None
    convert(args.pfx, password, args.out_dir)


if __name__ == "__main__":
    main()
