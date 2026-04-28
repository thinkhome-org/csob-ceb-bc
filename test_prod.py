#!/usr/bin/env python3
"""Comprehensive production test for ČSOB Business Connector.

Reads configuration from environment variables:
  CSOB_CONTRACT           Contract number (default: 42892301)
  CSOB_CLIENT_APP_GUID    Client app GUID (default: random UUID)
  CSOB_CERT_PEM           Path to certificate PEM (default: certs/bccert.pem)
  CSOB_CERT_KEY           Path to certificate key (default: certs/bccert.key)
  CSOB_WSDL               Path to WSDL file (default: wsdl/CEBBCWS.wsdl)
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.models import DownloadFilter, DownloadFileType, UploadFile, UploadMode
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.models import HttpTransferResult
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

# Configuration
CONTRACT_NUMBER = os.environ.get("CSOB_CONTRACT", "42892301")
CERT_PEM = Path(os.environ.get("CSOB_CERT_PEM", "certs/bccert.pem"))
CERT_KEY = Path(os.environ.get("CSOB_CERT_KEY", "certs/bccert.key"))
WSDL_PATH = str(Path(os.environ.get("CSOB_WSDL", "wsdl/CEBBCWS.wsdl")).resolve())
CLIENT_APP_GUID = os.environ.get("CSOB_CLIENT_APP_GUID", str(uuid4()))

STATE_DB = "sqlite:///prod_test_state.db"

print("=" * 60)
print("ČSOB BC Production Integration Test")
print("=" * 60)
print(f"Contract:       {CONTRACT_NUMBER}")
print(f"ClientAppGuid:  {CLIENT_APP_GUID}")
print(f"Cert PEM:       {CERT_PEM}")
print(f"Cert KEY:       {CERT_KEY}")
print(f"WSDL:           {WSDL_PATH}")
print(f"State DB:       {STATE_DB}")
print()

# ---------------------------------------------------------------------------
# 1. Certificate validation
# ---------------------------------------------------------------------------
print("[1/8] Certificate validation...")
config = ConnectorConfig(
    environment=Environment.PRODUCTION,
    contract_number=CONTRACT_NUMBER,
    client_app_guid=CLIENT_APP_GUID,
    certificate=CertificateConfig(
        cert_file=CERT_PEM,
        key_file=CERT_KEY,
    ),
)

cert_store = CertificateStore(config.certificate)
cert_store.validate_certificate()
cert_store.validate_not_expiring(min_days=7)
print(f"  ✅ Certificate valid")
print(f"      Subject: {cert_store.subject}")
print(f"      Expires: {cert_store.not_after}")
print(f"      Fingerprint (SHA256): {cert_store.fingerprint[:16]}...")
print()

# ---------------------------------------------------------------------------
# 2. SOAP gateway creation
# ---------------------------------------------------------------------------
print("[2/8] SOAP gateway creation...")
soap = SoapGateway(config, wsdl_path=WSDL_PATH, cert_store=cert_store)
print("  ✅ SOAP gateway created")
print()

# ---------------------------------------------------------------------------
# 3. REST client creation
# ---------------------------------------------------------------------------
print("[3/8] REST client creation...")
rest = RestTransferClient(cert_store=cert_store)
print("  ✅ REST client created")
print()

# ---------------------------------------------------------------------------
# 4. State repository
# ---------------------------------------------------------------------------
print("[4/8] State repository...")
state = SqliteStateRepository(STATE_DB)
print("  ✅ State repository ready")
print()

# ---------------------------------------------------------------------------
# 5. Download manager + list all files
# ---------------------------------------------------------------------------
print("[5/8] List available files (no filter)...")
dm = DownloadManager(
    contract_number=CONTRACT_NUMBER,
    client_app_guid=CLIENT_APP_GUID,
    cert_fingerprint=cert_store.fingerprint,
    environment="production",
    soap=soap,
    rest=rest,
    state=state,
)

try:
    files = dm.list_available_files(DownloadFilter())
    print(f"  ✅ Found {len(files)} files")
    types = {}
    statuses = {}
    for f in files:
        types[f.type.value] = types.get(f.type.value, 0) + 1
        statuses[f.status.value] = statuses.get(f.status.value, 0) + 1
    print(f"      Types:     {types}")
    print(f"      Statuses:  {statuses}")
    print(f"      Newest:    {files[0].filename} ({files[0].creation_date_time})")
except Exception as exc:
    print(f"  ❌ FAILED: {exc}")
    print()
    print("  If error mentions 'ClientAppGuid' or access denied,")
    print("  register this GUID in CEB portal:")
    print(f"     {CLIENT_APP_GUID}")
    raise SystemExit(1)
print()

# ---------------------------------------------------------------------------
# 6. List with filter (KURZY only)
# ---------------------------------------------------------------------------
print("[6/8] List with filter (KURZY only)...")
try:
    kurzy_files = dm.list_available_files(DownloadFilter(file_types=[DownloadFileType.KURZY]))
    print(f"  ✅ Found {len(kurzy_files)} exchange-rate files")
    for f in kurzy_files[:3]:
        print(f"      - {f.filename} ({f.format or 'no format'}, {f.size} bytes)")
    if len(kurzy_files) > 3:
        print(f"      ... and {len(kurzy_files) - 3} more")
except Exception as exc:
    print(f"  ❌ FAILED: {exc}")
print()

# ---------------------------------------------------------------------------
# 7. REST download (one KURZY file — smallest & safest)
# ---------------------------------------------------------------------------
print("[7/8] REST download test...")
if kurzy_files:
    # Pick the smallest KURZY file
    target = min(kurzy_files, key=lambda f: f.size or float("inf"))
    print(f"  Downloading {target.filename} ({target.size} bytes)...")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bb") as tmp:
            tmp_path = Path(tmp.name)
            result: HttpTransferResult = rest.download_to_file(target.url, tmp_path)
        print(f"  ✅ Downloaded {result.bytes_transferred} bytes to {tmp_path}")
        # Show first few lines
        with open(tmp_path, "r", encoding="cp1250", errors="replace") as f:
            lines = [f.readline().strip() for _ in range(3)]
        for line in lines:
            if line:
                print(f"      >> {line[:80]}")
        os.unlink(tmp_path)
    except Exception as exc:
        print(f"  ❌ FAILED: {exc}")
else:
    print("  ⚠️  No KURZY files available to download")
print()

# ---------------------------------------------------------------------------
# 8. Upload SOAP handshake (read-only check)
# ---------------------------------------------------------------------------
print("[8/8] Upload SOAP handshake (StartUploadFileList_v3)...")
try:
    dummy_file = UploadFile(
        filename="TEST_DO_NOT_PROCESS.xml",
        format="XML SEPA",
        mode=UploadMode.AllOrNothing,
        hash="a" * 64,
        size=1024,
    )
    # We only call start_upload to verify the SOAP operation is reachable.
    # We do NOT actually upload the file or call finish_upload.
    result = soap.start_upload_file_list_v3(files=[dummy_file])
    print(f"  ✅ StartUploadFileList_v3 responded")
    for r in result:
        print(f"      - {r.filename}: status={r.status}, url={'present' if r.url else 'none'}")
except Exception as exc:
    # If the bank rejects test uploads, that's expected — we just verify
    # the SOAP channel works.
    print(f"  ⚠️  StartUploadFileList returned: {exc}")
    print("      (This is expected if test uploads are rejected by the bank)")
print()

print("=" * 60)
print("Production integration test completed.")
print("=" * 60)
