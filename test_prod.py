#!/usr/bin/env python3
"""Read-only production test for ČSOB Business Connector."""

from pathlib import Path
from uuid import uuid4

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.models import DownloadFilter
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

# Configuration
CONTRACT_NUMBER = "42892301"
CERT_PEM = Path("certs/bccert.pem")
CERT_KEY = Path("certs/bccert.key")
WSDL_PATH = str(Path("wsdl/CEBBCWS.wsdl").resolve())

# Generate a fresh GUID for registration if needed
CLIENT_APP_GUID = str(uuid4())

print(f"Contract: {CONTRACT_NUMBER}")
print(f"ClientAppGuid: {CLIENT_APP_GUID}")
print(f"Cert: {CERT_PEM} + {CERT_KEY}")
print(f"WSDL: {WSDL_PATH}")
print()

config = ConnectorConfig(
    environment=Environment.PRODUCTION,
    contract_number=CONTRACT_NUMBER,
    client_app_guid=CLIENT_APP_GUID,
    certificate=CertificateConfig(
        cert_file=CERT_PEM,
        key_file=CERT_KEY,
    ),
)

print("Creating certificate store...")
cert_store = CertificateStore(config.certificate)
cert_store.validate_certificate()
print("✅ Certificate validated")

# Compute certificate fingerprint for profile key
from cryptography import x509
from cryptography.hazmat.primitives import hashes

cert = x509.load_pem_x509_certificate(open(CERT_PEM, "rb").read())
cert_fingerprint = cert.fingerprint(hashes.SHA256()).hex()
print(f"   Fingerprint: {cert_fingerprint[:16]}...")
print()

print("Creating SOAP gateway with local WSDL...")
soap = SoapGateway(config, wsdl_path=WSDL_PATH, cert_store=cert_store)
print("✅ SOAP gateway created")
print()

print("Creating REST client...")
rest = RestTransferClient(cert_store=cert_store)
print("✅ REST client created")
print()

print("Creating state repository...")
state = SqliteStateRepository("sqlite:///prod_test_state.db")
print("✅ State repository created")
print()

print("Creating download manager...")
dm = DownloadManager(
    contract_number=CONTRACT_NUMBER,
    client_app_guid=CLIENT_APP_GUID,
    cert_fingerprint=cert_fingerprint,
    environment="production",
    soap=soap,
    rest=rest,
    state=state,
)
print("✅ Download manager created")
print()

print("Calling list_available_files (read-only)...")
try:
    files = dm.list_available_files(DownloadFilter())
    print(f"✅ Success! Found {len(files)} files")
    for f in files:
        print(f"   - {f.filename} ({f.type.value}, {f.status.value})")
except Exception as exc:
    print(f"❌ Error: {exc}")
    print()
    print("If the error mentions 'ClientAppGuid' or access denied,")
    print("you need to register this GUID in the CEB portal:")
    print(f"   {CLIENT_APP_GUID}")
