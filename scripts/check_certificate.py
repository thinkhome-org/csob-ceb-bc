#!/usr/bin/env python3
"""Check certificate validity and expiry."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend


def check(cert_path: Path, min_days: int) -> None:
    pem = cert_path.read_bytes()
    cert = x509.load_pem_x509_certificate(pem, default_backend())

    print(f"Subject: {cert.subject}")
    print(f"Issuer: {cert.issuer}")
    print(f"Serial: {cert.serial_number}")

    if cert.not_valid_before_utc:
        print(f"Valid from: {cert.not_valid_before_utc}")
    if cert.not_valid_after_utc:
        print(f"Valid until: {cert.not_valid_after_utc}")
        days_left = (cert.not_valid_after_utc - datetime.now(timezone.utc)).days
        print(f"Days left: {days_left}")
        if days_left < min_days:
            print(f"WARNING: Certificate expires in {days_left} days (minimum {min_days})", file=sys.stderr)
            sys.exit(1)

    print("OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check certificate expiry")
    parser.add_argument("cert", type=Path, help="Path to PEM certificate")
    parser.add_argument("--min-days", type=int, default=7, help="Minimum days before expiry")
    args = parser.parse_args()
    check(args.cert, args.min_days)


if __name__ == "__main__":
    main()
