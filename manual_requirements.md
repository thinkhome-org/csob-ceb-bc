# ČSOB Business Connector - Key Requirements from Manual

## SOAP Operations

### GetDownloadFileList v4
- Input: ContractNumber, PrevQueryTimestamp (optional, max 45 days back), Filter (optional)
- Filter fields:
  - FileTypes/FileType (multiple): VYPIS, AVIZO, KURZY, IMPPROT
  - FileFormats/FileFormat (multiple): PDF, TXT, XML, BBGPC, BBMT940, BBTXT, BBBBF, SEPAXML, MT942, BBF, CAMT052
  - FileName: exact filename with extension
  - CreatedAfter, CreatedBefore: xsd:dateTime format YYYY-MM-DDTHH:MM:SS+ZZ:ZZ
  - ClientAppGuid: plus files created for this app instance
- Output: QueryTimestamp, FileList/FileDetail (Url, Filename, Type, Format, CreationDateTime, Size, UploadFileHash, Status, TicketId)
- Status values: R (retry/preparing), D (ready), F (permanent failure)
- Errors: 1000 (general), 1002 (no BC access), 1011 (cert not registered), 1012 (cert blocked), 1101 (rate limit)
- Rate limit: 30 calls per 20 minutes per contract+cert pair
- PrevQueryTimestamp behavior: if file has R status and no URL, MUST retry with same PrevQueryTimestamp
- F status does NOT block cursor advancement

### StartUploadFileList v3
- Input: ContractNumber, ClientAppGuid, FileList/ImportFileDetail
- ImportFileDetail fields: Filename (max 50), Hash (SHA256, 64 hex), Size, Format, Separator, Mode, SkipCheckDuplicates
- Formats: ABO, DUZ, MC TPS, MC ZPS, TXT TPS, TXT ZPS, XLS TPS, XLS ZPS, XLSX TPS, XLSX ZPS, MT101, XML SEPA, XML TPS, XML ZPS
- Separators: |, /, :, ::, ;, ;;
- Modes: IncludeIncorrect, OnlyCorrect, AllOrNothing, SignedAllOrNothing
- SkipCheckDuplicates: default false, ignored for SignedAllOrNothing
- Output: FileList/FileUrl (Filename, Hash, Status, Url, TicketId)
- Status values: R (rejected), U (upload ready)
- Errors: same as GetDownloadFileList

### FinishUploadFileList v2
- Input: ContractNumber, ClientAppGuid, FileList/FileId (Filename, Hash, NewFileId)
- Output: FileList/FileStatus (Filename, Hash, Status, TicketId)
- Status values: R (rejected), I (import started)
- Errors: same as above

## REST Service

### Download (HTTP GET)
- URL taken directly from SOAP response, never constructed manually
- Status codes:
  - 200 OK
  - 400 URL expired (15 days max) → permanent
  - 401 auth error → permanent
  - 404 file expired (15 days max) → permanent
  - 500 internal → retry
  - 503 unavailable → retry

### Upload (HTTP POST multipart)
- Content-Type: multipart/form-data
- Field name: "fileupload"
- Status codes:
  - 200/201 OK
  - 400 missing params → permanent
  - 401 auth → permanent
  - 403 unauthorized/URL expired → permanent
  - 408 timeout → retry
  - 500/502/503/504 → retry
  - JSON status in 200 response:
    - 450 file size exceeded → permanent
    - 451 bad extension → permanent
    - 452 bad file type → permanent
    - 453 antivirus fail → permanent
    - 454 bad URL/content → permanent
    - 455 timeout → retry
    - 456 timeout → retry

## Certificates
- Signature algorithm: SHA256 or stronger
- Key length: RSA min 2048 bits
- Key Usage (if present): Digital Signature OR Key Encipherment
- Extended Key Usage (if present): SSL Client Authentication
- TLS: min 1.2, recommended 1.3
- CA bundles accepted: I.CA, PostSignum, ČSOB internal CA

## Demo Environment
- SOAP URL: https://testceb-bc.csob.cz/cebbc/api
- REST download: https://testceb-bc.csob.cz/ceb-mock/download?id=...
- REST upload: https://testceb-bc.csob.cz/ceb-mock/upload?id=...
- ContractNumber ignored
- Filters ignored
- No rate limit enforcement
- Auth required but doesn't affect content
- Static responses

## SOAP Headers
- Content-Type: text/xml; charset=utf-8
- SOAPAction: "{operation}" (from WSDL soap:operation)
- Content-Length: body length

## Time Format
- All timestamps: xsd:dateTime YYYY-MM-DDTHH:MM:SS+ZZ:ZZ

## WSDL
- https://www.csob.cz/portal/documents/10710/15100026/cebbc-wsdl.zip
