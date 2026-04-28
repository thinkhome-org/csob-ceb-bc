# Mapování implementační příručky → SDK API

Tento dokument mapuje sekce oficiální příručky *ČSOB Business Connector – Implementační příručka pro automatické stahování a odesílání souborů* na třídy a metody Python SDK.

---

## 1. Změny od 20. října 2024 (str. 1)

| Příručka | SDK |
|----------|-----|
| `GetDownloadFileList` v4 | `SoapGateway.get_download_file_list_v4()` |
| `StartUploadFileList` v3 | `SoapGateway.start_upload_file_list_v3()` |
| `FinishUploadFileList` v2 | `SoapGateway.finish_upload_file_list_v2()` |
| Hash MD5 → SHA256 | `UploadFile.hash` validátor (64 hex) |
| Upload pouze Multipart | `AsyncRestTransferClient.upload_multipart()` |

---

## 2. Rozhraní služby (str. 11–13)

### 2.1 Autentizace (str. 11)

| Příručka | SDK |
|----------|-----|
| mTLS (vzájemná autentizace) | `CertificateStore` + `SoapGateway._create_transport()` + `AsyncRestTransferClient` |
| Klientský certifikát | `CertificateConfig` (cert_file + key_file nebo pfx_file) |
| Registrace certifikátu v CEB | Mimo SDK – provede se ručně v CEB portálu |

### 2.2 Stahování souborů (str. 12)

| Příručka | SDK |
|----------|-----|
| `GetDownloadFileList` → seznam URL | `DownloadManager.list_available_files()` |
| `GET(URL)` → stažení souboru | `DownloadManager.download_new_files()` |
| Dvě vlákna (manažer + downloader) | SDK poskytuje low-level API; vlákna řídí volající aplikace |
| Monitorování nových souborů | `DownloadBatchResult.has_pending_files` + `cursor_advanced` |

### 2.3 Odesílání souborů (str. 13)

| Příručka | SDK |
|----------|-----|
| `StartUploadFileList` → URL pro upload | `UploadManager.upload_payment_batch()` |
| `POST(URL, filename)` → `newFileId` | `AsyncRestTransferClient.upload_multipart()` |
| `FinishUploadFileList` → status | `UploadManager.upload_payment_batch()` (interně, async) |
| Stažení protokolu o importu | `ImportProtocolManager.poll_import_protocols()` |

---

## 3. Webová služba SOAP/HTTPS (str. 13–18)

### 3.1 `GetDownloadFileList` (str. 13–15)

| Příručka | SDK |
|----------|-----|
| `ContractNumber` | `ConnectorConfig.contract_number` |
| `PrevQueryTimestamp` | `StateRepository.get_profile_cursor()` / `set_profile_cursor()` |
| `Filter/FileTypes` | `DownloadFilter.file_types` (`DownloadFileType` enum) |
| `Filter/FileFormats` | `DownloadFilter.file_formats` |
| `Filter/FileName` | `DownloadFilter.filename` |
| `Filter/CreatedAfter` / `CreatedBefore` | `DownloadFilter.created_after` / `created_before` |
| `Filter/ClientAppGuid` | `DownloadFilter.client_app_guid` (UUID validace) |
| `QueryTimestamp` | `DownloadBatchResult.query_timestamp` |
| `FileList/FileDetail/Url` | `DownloadFile.url` |
| `FileList/FileDetail/Status` (R/D/F) | `DownloadFile.status` (`DownloadFileStatus` enum) |
| `FileList/FileDetail/UploadFileHash` | `DownloadFile.upload_file_hash` (SHA256, pouze IMPPROT) |
| Cursor se neposune při `R` souborech | `DownloadBatchResult.cursor_advanced == False` |
| Chyby 1000, 1002, 1011, 1012, 1101 | `SoapFaultCode` enum + `CsobBCServerError`, `CsobBCContractDisabledError`, … |

### 3.2 `StartUploadFileList` (str. 15–17)

| Příručka | SDK |
|----------|-----|
| `ContractNumber` | `ConnectorConfig.contract_number` |
| `ClientAppGuid` | `ConnectorConfig.client_app_guid` (UUID validace) |
| `FileList/ImportFileDetail/Filename` | `UploadFile.filename` (max 50 znaků) |
| `FileList/ImportFileDetail/Hash` | `UploadFile.hash` (SHA256, 64 hex) |
| `FileList/ImportFileDetail/Size` | `UploadFile.size` |
| `FileList/ImportFileDetail/Format` | `UploadFile.format` (regex: ABO, DUZ, …) |
| `FileList/ImportFileDetail/Separator` | `UploadFile.separator` (\|, /, :, ::, ;, ;;) |
| `FileList/ImportFileDetail/Mode` | `UploadFile.mode` (`UploadMode` enum) |
| `FileList/ImportFileDetail/SkipCheckDuplicates` | `UploadFile.skip_check_duplicates` |
| `FileList/FileUrl/Status` (R/U) | `UploadStartResult.status` (`UploadStartStatus` enum) |

### 3.3 `FinishUploadFileList` (str. 17–18)

| Příručka | SDK |
|----------|-----|
| `FileList/FileId/Filename` | `UploadFinishResult.filename` |
| `FileList/FileId/Hash` | `UploadFinishResult.hash` (SHA256 validace) |
| `FileList/FileId/NewFileId` | `UploadFinishResult.new_file_id` (z REST response) |
| `FileList/FileStatus/Status` (R/I) | `UploadFinishResult.status` (`UploadFinishStatus` enum) |

### 3.4 Ochranný interval (str. 18)

| Příručka | SDK |
|----------|-----|
| 30 volání / 20 minut | `RateLimitConfig.soap_calls=30`, `per_seconds=1200` |
| `TokenBucketRateLimiter` | Používá se v produkci, DEMO ho přeskakuje |
| `short_poll_seconds` | `RateLimitConfig.short_poll_seconds` (10 s default) pro pending soubory |

### 3.5 WSDL a adresa služby (str. 18)

| Příručka | SDK |
|----------|-----|
| `https://ceb-bc.csob.cz/cebbc/api` | `SoapGateway.PROD_URL` |
| `https://testceb-bc.csob.cz/cebbc/api` | `SoapGateway.DEMO_URL` |
| Lokální WSDL | `wsdl/CEBBCWS.wsdl` (nahrazená `${BankAdress}` placeholder) |

---

## 4. REST služba HTTP download/upload (str. 18–20)

### 4.1 HTTP GET – download (str. 19)

| Příručka | SDK |
|----------|-----|
| `GET /ExtFileHubDown/v2/download?id=…` | `AsyncRestTransferClient.download_to_file()` |
| Status 200 OK | Úspěch |
| Status 400/401/404 | Permanentní chyba |
| Status 500/503 | Retryable chyba |

### 4.2 HTTP POST – upload (str. 19–20)

| Příručka | SDK |
|----------|-----|
| `POST /ExtFileHubUp/v2/upload?id=…` | `AsyncRestTransferClient.upload_multipart()` |
| `Content-Type: multipart/form-data` | Generuje `httpx` automaticky |
| `Content-Disposition: form-data; name="fileupload"; filename="…"` | Generuje `httpx` automaticky |
| JSON odpověď `{Status, ExtFileUrl, NewFileId}` | `RestUploadResult` model |
| Status 200/201 | Úspěch |
| Status 450–454 | Permanentní chyba (`CsobBCHttpError` permanent=True) |
| Status 455–456 | Retryable chyba (`CsobBCHttpError` retryable=True) |

---

## 5. Technické požadavky (str. 21–23)

### 5.1 Certifikát (str. 21–22)

| Příručka | SDK |
|----------|-----|
| I.CA / PostSignum / interní ČSOB | `CertificateStore.validate_certificate()` kontroluje EKU |
| SHA256 podpis | Kontrolováno v `validate_certificate()` |
| RSA ≥ 2048 bitů | Kontrolováno v `validate_certificate()` |
| SSL klientská autentizace | Kontrolováno v `validate_certificate()` |
| TLS 1.3 doporučeno, min. 1.2 | `requests` / `httpx` vyjednávají automaticky |

### 5.2 HTTP a SOAP (str. 23)

| Příručka | SDK |
|----------|-----|
| HTTP 1.1 | `httpx` / `requests` |
| SOAP 1.1 | `zeep` generuje automaticky |
| `Content-Type: text/xml; charset=utf-8` | `zeep` generuje automaticky |
| `SOAPAction: "{operace}"` | `zeep` generuje z WSDL (`soapAction` atribut) |

---

## 6. Formáty souborů (str. 24–26)

### 6.1 Kurzovní lístek – QUOTES (str. 24–25)

| Příručka | SDK |
|----------|-----|
| Fixed-width formát (32/76/124 znaků) | `formats.quotes.parse_quotes()` |
| Záznam 01 – hlavička | `QuotesHeader` |
| Záznam 02 – metadata | `QuotesMetadata` |
| Záznam 03 – kurzy | `QuotesRate` (včetně `Decimal` pro kurzy) |
| Encoding CP1250 | Default v `parse_quotes()`, konfigurovatelné |

### 6.2 Protokol o importu (str. 25)

| Příručka | SDK |
|----------|-----|
| XML PAIN.002 (ISO20022) | SDK vrací raw soubor; parsing je na volající aplikaci |
| Typ souboru `IMPPROT` | `DownloadFileType.IMPPROT` |
| `upload_file_hash` pro párování | `ImportProtocolManager` |

### 6.3 Podepsané dávky (str. 26)

| Příručka | SDK |
|----------|-----|
| CAdES-BES formát | SDK nepodporuje vytváření podpisu |
| `Mode=SignedAllOrNothing` | `UploadMode.SignedAllOrNothing` |
| `SkipCheckDuplicates` se ignoruje | Validátor zakáže `skip_check_duplicates=True` pro tento mód |

---

## 7. Testovací demo prostředí (str. 21)

| Příručka | SDK |
|----------|-----|
| Statické odpovědi | DEMO prostředí vrací statické odpovědi |
| Ignorované `ContractNumber` | `ConnectorConfig.contract_number` se stále posílá, banka ignoruje |
| Ignorované filtry | `DownloadFilter` se stále posílá, banka ignoruje |
| Nezbytná autentizace certifikátem | `CertificateStore` validuje certifikát i v DEMO |
| `Environment.DEMO` | `ConnectorConfig.environment = Environment.DEMO` |
