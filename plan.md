 ## 1. Executive Summary

  SDK csob-ceb-business-connector-sdk má být produkční Python knihovna pro automatizované
  stahování a odesílání souborů přes ČSOB CEB Business Connector.

  Základní architektura:

  - SOAP/HTTPS vrstva pro orchestraci procesů: GetDownloadFileList v4,
    StartUploadFileList v3, FinishUploadFileList v2.
  - REST/HTTPS vrstva pro vlastní přenos souborů přes URL vrácené SOAP službou.
  - mTLS všude: SOAP i REST používají vzájemnou autentizaci klientským certifikátem.
  - Stavová vrstva je povinná, ne volitelný detail. Bez perzistence nelze bezpečně řešit
    PrevQueryTimestamp, opakované pollingy, duplicitní uploady, NewFileId, importní
    protokoly ani crash recovery.
  - SDK musí být konzervativní: nikdy nesmí posouvat PrevQueryTimestamp, dokud nejsou
    bezpečně zpracované všechny relevantní soubory.
  - SDK nesmí konstruovat vlastní ČSOB REST URL. Vždy použije URL přesně tak, jak ji
    vrátila SOAP služba.

  Doporučený import package: csob_ceb_bc. PyPI/distribuční název: csob-ceb-business-
  connector-sdk.

  ## 2. Hlavní Předpoklady A Otevřené Otázky

  Doložená fakta:

  | Oblast | Doloženo |
  |---|---|
  | SOAP API | SOAP 1.1 přes HTTPS, mTLS |
  | REST API | HTTPS GET pro download, HTTPS POST multipart pro upload |
  | WSDL | https://www.csob.cz/portal/documents/10710/15100026/cebbc-wsdl.zip |
  | Produkční SOAP endpoint | https://ceb-bc.csob.cz/cebbc/api |
  | Demo SOAP endpoint | https://testceb-bc.csob.cz/cebbc/api |
  | REST download prod | URL vrácená SOAP službou, typicky pod `https://ceb-bc.csob.cz/ExtFileHubDown/...` |
  | REST upload prod | URL vrácená SOAP službou, typicky pod `https://ceb-bc.csob.cz/ExtFileHubUp/...` |
  | Demo REST | URL vrácené SOAP službou, v příručce uvedené jako `testceb-bc.csob.cz/ceb-mock/...` |
  | Ochranný limit | 30 SOAP volání za 20 minut pro dvojici číslo smlouvy / klientský certifikát; banka může hodnotu změnit |
  | Upload hash | SHA256 pro StartUploadFileList v3 a FinishUploadFileList v2 |
  | Upload transport | pouze multipart/form-data; octet-stream nepoužívat |

  Další doložené implementační body z příručky:

  - Od 20. října 2024 jsou pro nové implementace relevantní verze
    `GetDownloadFileList v4`, `StartUploadFileList v3` a `FinishUploadFileList v2`.
  - Starší upload služby nepoužívat; podle příručky mělo být přechodné období ukončeno
    31. března 2025.
  - Upload přes `octet-stream` je deprecated a SDK ho nesmí implementovat jako produkční
    cestu.
  - Pro download platí 45denní časové okno: pokud `PrevQueryTimestamp` není uveden,
    použije se čas 45 dní zpět; na čas starší než 45 dní v minulosti se nepřihlíží.
  - Časové údaje pro SOAP requesty jsou ve formátu `xsd:dateTime`
    `YYYY-MM-DDTHH:MM:SS+ZZ:ZZ`.
  - REST download URL a REST upload URL se vždy použijí beze změny tak, jak je vrátí
    příslušná SOAP operace.
  - Demo prostředí vyžaduje certifikátovou autentizaci, ale podle příručky nevyžaduje
    registraci certifikátu v CEB, ignoruje `ContractNumber`, ignoruje filtry
    `GetDownloadFileList`, neudržuje stav mezi voláními a nevyžaduje ochranný interval.
  - V CEB portálu musí být povolené konkrétní operace: kurzovní lístky, výpisy, avíza,
    upload platebních dávek a případně upload podepsaných platebních dávek pro konkrétní
    účty.
  - Soubory vzniklé před povolením stahování v nastavení Business Connectoru pro konkrétní
    účet služba podle příručky nevrátí.

  Otevřené otázky:

  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB přesné XML namespaces, typy a
    binding názvy po rozbalení aktuálního WSDL ZIP.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB aktuální dostupnost WSDL ZIP;
    při kontrole dne 2026-04-27 URL z příručky vrátila chybovou HTML stránku místo ZIP
    archivu.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda se v odpovědi
    StartUploadFileList v3 pole Hash ve WSDL skutečně jmenuje a chová jako SHA256; text
    příručky u výstupu obsahuje historickou formulaci s MD5, ale verze v3 je popsána jako
    SHA256.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB přesný název HTTP hlavičky, ve
    které má být podle příručky identita klienta u REST služby obsažena, pokud ji
    klientská knihovna musí nastavovat ručně. Bez potvrzení ji SDK nemá vymýšlet.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB přesný minimální interval po SOAP
    Fault 1101; příručka uvádí ochranné okno 30/20 minut a upozorňuje, že soustavné
    volání může blokaci prodlužovat.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda lze po expiraci download URL
    získat novou URL opakováním GetDownloadFileList, nebo se má stav považovat za
    konečný.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB přesné časování generování
    importních protokolů po stavu I.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB kompletní XSD a formátové
    specifikace výpisů, avíz a platebních dávek mimo rozsah této příručky.

  ## 3. Doporučené Cíle SDK

  - Bezpečná produkční automatizace download/upload workflow.
  - Jednoznačné oddělení SOAP orchestrace od REST přenosu.
  - Stavová idempotence pro ERP/accounting integrace.
  - Podpora PEM certifikátu a klíče, CRT/KEY páru a praktická podpora P12/PFX přes
    konverzi.
  - Striktní respektování ochranného intervalu.
  - Bezpečné opakování po výpadcích bez duplicitního uploadu.
  - Testovatelná architektura s mockovatelným SOAP/REST rozhraním.
  - Auditní logy bez úniku privátních klíčů, bankovních dat a citlivých identifikátorů.

  ## 4. Non-Goals SDK

  SDK záměrně nemá:

  - Vytvářet nebo autorizovat CAdES-BES podpisy pro podepsané platební dávky.
  - Nahrazovat software třetích stran pro vytvoření podpisu CAdES-BES. Podepsaný soubor
    může pouze převzít jako hotový vstup.
  - Nahrazovat CEB portál pro registraci certifikátů a povolení operací.
  - Parsovat kompletní účetní význam všech bankovních formátů.
  - Vymýšlet endpointy, XSD pole nebo business pravidla mimo dokumentaci.
  - Automaticky opakovat upload odmítnutý bankou se stavem R.
  - Logovat obsah platebních dávek, výpisů, avíz nebo importních protokolů.
  - Obcházet bankovní ochranný interval nebo paralelně navyšovat počet volání pro stejný
    kontrakt/certifikát.

  Podepsané dávky podle příručky:

  - mají navíc interní elektronický podpis ve formátu CAdES-BES a příponu `.p7m`, například
    `125456_10000141.zps.p7m`;
  - nejsou textovým souborem, ale textová informace v nich podle příručky není šifrována;
  - musí být podepsané certifikátem používaným v CEB portálu k autorizaci transakcí,
    nikoli klientským přístupovým certifikátem určeným pro Business Connector.

  ## 5. High-Level Architecture

  SDK se rozdělí na tyto vrstvy:

  - SOAP orchestration layer: volá GetDownloadFileList v4, StartUploadFileList v3,
    FinishUploadFileList v2, mapuje SOAP Faulty a loguje TicketId.
  - REST transfer layer: provádí streaming GET download a multipart POST upload přes URL
    vrácené SOAPem.
  - Certificate layer: načítá certifikát, klíč, CA bundle, validuje expiraci a připravuje
    mTLS konfiguraci.
  - Domain layer: Pydantic modely, enumy, validace vstupů.
  - Workflow managers: download, upload a import protocol workflow.
  - State persistence: ukládá timestampy, file records, upload attempts, NewFileId,
    idempotency keys a retry stavy.
  - Logging/audit: strukturované bezpečné logování, korelace, redakce.
  - Public API: jednoduché facade API pro ERP a scheduled jobs.

  ## 6. Mermaid Architecture Diagram

  ```mermaid
  flowchart LR
      ERP[ERP / účetní systém] --> API[BusinessConnectorClient]

      API --> DM[DownloadManager]
      API --> UM[UploadManager]
      API --> IPM[ImportProtocolManager]

      DM --> SOAP[SoapGateway]
      UM --> SOAP
      IPM --> SOAP

      DM --> REST[RestTransferClient]
      UM --> REST
      IPM --> REST

      SOAP --> CERT[CertificateStore / mTLS]
      REST --> CERT

      DM --> STATE[StateRepository]
      UM --> STATE
      IPM --> STATE

      API --> LOG[AuditLogger]
      SOAP --> LOG
      REST --> LOG
      STATE --> LOG

      SOAP --> CSOBSOAP[ČSOB SOAP/HTTPS]
      REST --> CSOBREST[ČSOB REST/HTTPS GET/POST]
  ```

  ## 7. Doporučená Struktura Repozitáře

  ```text
  csob-ceb-business-connector-sdk/
    pyproject.toml
    README.md
    CHANGELOG.md
    LICENSE
    src/
      csob_ceb_bc/
        __init__.py
        client.py
        config.py
        models.py
        errors.py
        soap/
          __init__.py
          gateway.py
          zeep_client.py
          faults.py
          versions.py
        rest/
          __init__.py
          transfer.py
          multipart.py
        certificates/
          __init__.py
          store.py
          pfx.py
          validation.py
        downloads/
          __init__.py
          manager.py
          filters.py
        uploads/
          __init__.py
          manager.py
          hashing.py
        import_protocols/
          __init__.py
          manager.py
        state/
          __init__.py
          base.py
          file_repository.py
          sqlite_repository.py
          schema.sql
        retry.py
        rate_limit.py
        logging.py
        redaction.py
        time.py
    tests/
      unit/
      integration/
      fixtures/
        soap/
        rest/
        certs/
    docs/
      quickstart.md
      certificates.md
      configuration.md
      downloads.md
      uploads.md
      import-protocols.md
      troubleshooting.md
      security.md
      operations-runbook.md
    examples/
      download_new_files.py
      upload_payment_batch.py
      scheduled_polling.py
      config.yaml
    scripts/
      convert_pfx_to_pem.py
      check_certificate.py
  ```

  ## 8. Python Package / Module Structure

  | Modul | Odpovědnost |
  |---|---|
  | csob_ceb_bc.client | Public facade BusinessConnectorClient |
  | csob_ceb_bc.config | Pydantic settings, env/YAML konfigurace |
  | csob_ceb_bc.models | Doménové modely a enumy |
  | csob_ceb_bc.errors | Výjimky a error klasifikace |
  | csob_ceb_bc.soap | Zeep integrace, SOAP operace, Fault mapping |
  | csob_ceb_bc.rest | GET/POST přenosy, streaming, multipart |
  | csob_ceb_bc.certificates | PEM/PFX handling, expirace, mTLS |
  | csob_ceb_bc.downloads | Download workflow, timestamp pravidla |
  | csob_ceb_bc.uploads | Upload workflow, SHA256, finalizace |
  | csob_ceb_bc.import_protocols | Polling a párování importních protokolů |
  | csob_ceb_bc.state | File/SQLite/SQLAlchemy state backends |
  | csob_ceb_bc.retry | Retry policies |
  | csob_ceb_bc.rate_limit | Token bucket pro ochranný interval |
  | csob_ceb_bc.logging | Audit logger, correlation IDs |
  | csob_ceb_bc.redaction | Maskování citlivých hodnot |

  ## 9. pyproject.toml Recommendations

  Runtime dependencies:

  [project]
  name = "csob-ceb-business-connector-sdk"
  requires-python = ">=3.11"
  dependencies = [
    "zeep>=4.2",
    "requests>=2.32",
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "tenacity>=8.2",
    "cryptography>=42",
    "structlog>=24",
    "platformdirs>=4",
    "certifi>=2024.0",
  ]

  Volitelné extras:

  [project.optional-dependencies]
  pfx = ["cryptography>=42"]
  sqlite = ["sqlalchemy>=2.0"]
  async = ["httpx>=0.27", "anyio>=4"]
  yaml = ["PyYAML>=6.0"]
  dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "respx>=0.21",
    "responses>=0.25",
    "requests-mock>=1.12",
    "ruff>=0.5",
    "mypy>=1.10",
    "types-requests",
    "build",
    "twine",
  ]

  ## 10. Core Classes And Responsibilities

  class BusinessConnectorClient:
      def list_available_files(self, filter: DownloadFilter) -> list[DownloadFile]: ...
      def download_new_files(self, filter: DownloadFilter, target_dir: Path) ->
  list[DownloadedFileRecord]: ...
      def upload_payment_batch(self, file: Path, metadata: UploadFile) ->
  UploadFinishResult: ...
      def poll_import_protocols(self) -> list[ImportProtocolRecord]: ...
      def resume_pending(self) -> None: ...

  class SoapGateway:
      def get_download_file_list_v4(...) -> DownloadListResult: ...
      def start_upload_file_list_v3(...) -> UploadStartResult: ...
      def finish_upload_file_list_v2(...) -> UploadFinishResult: ...

  class RestTransferClient:
      def download_to_file(self, url: str, target: Path) -> HttpTransferResult: ...
      def upload_multipart(self, url: str, file: Path, filename: str) -> RestUploadResult: ...

  class CertificateStore:
      def build_requests_session(self) -> requests.Session: ...
      def build_httpx_client(self) -> httpx.Client: ...
      def validate_not_expiring(self) -> None: ...

  class StateRepository:
      def transaction(self): ...
      def get_profile_cursor(self, profile_key: str) -> datetime | None: ...
      def save_upload_new_file_id(self, attempt_id: str, new_file_id: str) -> None: ...

  Další klíčové třídy: DownloadManager, UploadManager, ImportProtocolManager,
  RetryPolicy, RateLimiter, AuditLogger, CsobBCError.

  ## 11. Public SDK API Design

  Inicializace produkce s PEM/KEY:

  from pathlib import Path
  from csob_ceb_bc import BusinessConnectorClient, ConnectorConfig, CertificateConfig,
  Environment

  client = BusinessConnectorClient.from_config(
      ConnectorConfig(
          environment=Environment.PRODUCTION,
          contract_number="TODO_CONTRACT",
          client_app_guid="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
          certificate=CertificateConfig(
              cert_file=Path("/secure/certs/bccert.crt"),
              key_file=Path("/secure/certs/bccert.key"),
              ca_bundle=None,
          ),
          state_url="sqlite:////var/lib/csob-ceb/state.db",
      )
  )

  Inicializace demo/sandbox:

  config = ConnectorConfig(
      environment=Environment.DEMO,
      contract_number="ignored-in-demo",
      client_app_guid="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      certificate=CertificateConfig(
          cert_file=Path("demo.crt"),
          key_file=Path("demo.key"),
      ),
  )
  client = BusinessConnectorClient.from_config(config)

  P12/PFX konfigurace:

  config = ConnectorConfig(
      environment=Environment.PRODUCTION,
      contract_number="TODO_CONTRACT",
      client_app_guid="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      certificate=CertificateConfig(
          pfx_file=Path("/secure/certs/bccert.pfx"),
          pfx_password_env="CSOB_BC_PFX_PASSWORD",
      ),
  )

  Strategie: SDK při startu načte PFX přes cryptography, zvaliduje certifikát a vytvoří
  dočasné PEM soubory s právy 0600, pokud použitá HTTP knihovna vyžaduje souborové PEM
  vstupy.

  List available files:

  files = client.list_available_files(
      DownloadFilter(file_types=["VYPIS", "AVIZO", "KURZY"])
  )

  Download new files:

  downloaded = client.download_new_files(
      filter=DownloadFilter(file_types=["VYPIS", "AVIZO"]),
      target_dir=Path("/data/csob/inbox"),
  )

  Download only statements:

  client.download_new_files(
      filter=DownloadFilter(file_types=["VYPIS"]),
      target_dir=Path("/data/csob/statements"),
  )

  Download import protocols:

  protocols = client.poll_import_protocols()

  Upload payment batch:

  result = client.upload_payment_batch(
      file=Path("/data/csob/outbox/payments.xml"),
      metadata=UploadFile(
          filename="payments.xml",
          format="XML SEPA",
          mode="AllOrNothing",
          skip_check_duplicates=False,
      ),
  )

  Finish upload samostatně:

  start = client.uploads.start_upload(file, metadata)
  rest = client.uploads.transfer_file(start)
  finish = client.uploads.finish_upload(start, rest)

  Resume after failure:

  client.resume_pending()

  Scheduled polling example:

  import time

  while True:
      client.resume_pending()
      client.download_new_files(DownloadFilter(file_types=["VYPIS", "AVIZO"]), Path("/inbox"))
      client.poll_import_protocols()
      time.sleep(60)

  ## 12. Data Models

  Doporučené modely:

  class ConnectorConfig(BaseModel): ...
  class CertificateConfig(BaseModel): ...
  class DownloadFilter(BaseModel): ...
  class DownloadFile(BaseModel): ...
  class UploadFile(BaseModel): ...
  class UploadStartResult(BaseModel): ...
  class RestUploadResult(BaseModel): ...
  class UploadFinishResult(BaseModel): ...
  class ImportProtocolRecord(BaseModel): ...
  class SoapFaultInfo(BaseModel): ...
  class HttpTransferResult(BaseModel): ...
  class StateRecord(BaseModel): ...

  Enumy:

  class DownloadFileType(str, Enum):
      VYPIS = "VYPIS"
      AVIZO = "AVIZO"
      KURZY = "KURZY"
      IMPPROT = "IMPPROT"

  class DownloadFileStatus(str, Enum):
      R = "R"  # připravuje se
      D = "D"  # lze stáhnout
      F = "F"  # permanentní chyba

  class UploadMode(str, Enum):
      IncludeIncorrect = "IncludeIncorrect"
      OnlyCorrect = "OnlyCorrect"
      AllOrNothing = "AllOrNothing"
      SignedAllOrNothing = "SignedAllOrNothing"

  class UploadStartStatus(str, Enum):
      R = "R"  # odmítnuto
      U = "U"  # možno zahájit upload

  class UploadFinishStatus(str, Enum):
      R = "R"  # odmítnuto
      I = "I"  # import zahájen

  Download formáty doložené v příručce: PDF, TXT, XML, BBGPC, BBMT940, BBTXT, BBBBF,
  SEPAXML, MT942, BBF, CAMT052; pro kurzovní lístky se FileFormat ignoruje / není uveden.

  Upload formáty doložené v příručce: ABO, DUZ, MC TPS, MC ZPS, TXT TPS, TXT ZPS, XLS
  TPS, XLS ZPS, XLSX TPS, XLSX ZPS, MT101, XML SEPA, XML TPS, XML ZPS.

  Model `UploadFile` musí validovat:

  - `filename` max. 50 znaků;
  - `hash` generovaný SDK jako SHA256, 64 hex znaků;
  - `separator` pouze z množiny `|`, `/`, `:`, `::`, `;`, `;;`, nebo `None`;
  - `skip_check_duplicates=False` jako default;
  - při `mode=SignedAllOrNothing` nesmí SDK slibovat vypnutí duplicit, protože banka podle
    příručky příznak ignoruje.

  ## 13. SOAP Client Design

  SOAP klient:

  - používá zeep s requests.Session nakonfigurovanou na mTLS;
  - načítá WSDL z lokálně uloženého ZIP/cache, ne nutně při každém běhu z internetu;
  - serializuje requesty přes WSDL typy, ne ruční stringy;
  - mapuje SOAP Fault na CsobBCSoapFault;
  - z každé odpovědi i chyby vytahuje TicketId, pokud je dostupný;
  - odděluje verze operací v modulech nebo metodách.

  Operace:

  - GetDownloadFileList v4: vstup ContractNumber, volitelný PrevQueryTimestamp, volitelný
    Filter.
  - StartUploadFileList v3: vstup ContractNumber, ClientAppGuid, seznam souborů s
    Filename, Hash, Size, Format, Separator, Mode, SkipCheckDuplicates.
  - FinishUploadFileList v2: vstup ContractNumber, ClientAppGuid, Filename, Hash,
    NewFileId.

  Obecné požadavky na HTTP/SOAP z příručky:

  | Požadavek | Hodnota |
  |---|---|
  | SOAP verze | SOAP 1.1 |
  | HTTP verze | HTTP 1.1 nebo HTTP 1.0 |
  | Povinný `Content-Type` | `text/xml; charset=utf-8` |
  | Povinný `SOAPAction` | hodnota atributu `soapAction` z WSDL pro danou operaci |
  | Povinný `Content-Length` | délka těla zprávy v bajtech |

  SOAP odpovědi a SOAP Faulty mají obsahovat `TicketId`, který SDK musí uložit do
  strukturovaného logu a do auditní stopy. `TicketId` se nesmí ztratit ani při převodu
  SOAP Faultu na SDK výjimku.

  Verze operací podle příručky:

  | Operace | Použitá verze v SDK | Důvod |
  |---|---|---|
  | `GetDownloadFileList` | v4 | změna `UploadFileHash` z MD5 na SHA256 |
  | `StartUploadFileList` | v3 | SHA256 místo MD5, možnost `SkipCheckDuplicates` |
  | `FinishUploadFileList` | v2 | SHA256 místo MD5 |

  TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB přesné názvy operací a namespace v
  aktuálním WSDL.

  ## 14. REST Transfer Client Design

  GET download:

  - použít URL přesně ze SOAP odpovědi;
  - použít streaming;
  - zapisovat do *.part souboru;
  - po úspěšném dokončení a případné kontrole velikosti provést atomický rename;
  - nelogovat obsah souboru.
  - REST download URL v produkci je podle příručky vracená typicky pod
    `https://ceb-bc.csob.cz/ExtFileHubDown/...`; demo URL typicky pod
    `https://testceb-bc.csob.cz/ceb-mock/download?id=...`. SDK ale nesmí tyto URL
    skládat ručně.

  POST upload:

  - použít pouze multipart/form-data;
  - MIME part s názvem pole fileupload podle příručky;
  - Content-Type partu application/octet-stream;
  - nepoužívat deprecated octet-stream upload URL;
  - parsovat JSON odpověď a uložit NewFileId.
  - REST upload URL v produkci je podle příručky vracená typicky pod
    `https://ceb-bc.csob.cz/ExtFileHubUp/...`; demo URL typicky pod
    `https://testceb-bc.csob.cz/ceb-mock/upload?id=...`. SDK ale nesmí tyto URL skládat
    ručně.

  Multipart požadavek podle příručky:

  - HTTP method: `POST`;
  - `Content-Type`: `multipart/form-data` s boundary;
  - MIME part `Content-Type`: `application/octet-stream`;
  - pole podle příkladu: `name="fileupload"`;
  - filename v `Content-Disposition`; pokud obsahuje české znaky, použít MIME encoding
    podle RFC 2047.

  REST upload odpověď při úspěchu má JSON tvar:

  ```json
  {
    "Status": "201",
    "ExtFileUrl": "",
    "NewFileId": "QqGQl_Zk5e9RGphGoKv4YbAihKSeTadC"
  }
  ```

  `ExtFileUrl` je podle příručky nepoužito. `NewFileId` je identifikátor odeslaného
  souboru a SDK ho musí persistovat před voláním `FinishUploadFileList v2`.

  TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB rozdíl mezi příkladem multipart
  hlavičky `Content-Disposition: form-data; name="fileupload"` a tabulkou v příručce,
  kde je uvedeno `Content-Disposition: attachment; filename="..."`.

  Checksum:

  - u uploadu se počítá SHA256 před StartUploadFileList.
  - u downloadu příručka neuvádí hash staženého souboru, lze kontrolovat alespoň
    velikost, pokud je ve SOAP odpovědi Size.
  - TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda existuje bankou garantovaný
    checksum pro download.

  ## 15. Certificate And mTLS Design

  Podporované vstupy:

  - PEM certifikát + PEM privátní klíč;
  - CRT/KEY pár;
  - P12/PFX přes konverzi do PEM;
  - volitelný CA bundle.

  Onboarding podle příručky:

  1. Povolit službu ČSOB Business Connector u smlouvy CEB.
  2. Získat certifikát od podporované certifikační autority nebo přímo od banky.
  3. Registrovat certifikát pro Business Connector v CEB portálu.
  4. V CEB portálu povolit konkrétní operace a účty.
  5. Nakonfigurovat klientskou aplikaci se stejným certifikátem a privátním klíčem.

  Certifikát vydaný bankou je podle příručky při žádosti přes CEB portál rovnou zařazen
  do seznamu registrovaných certifikátů v kontraktu. Certifikát vydaný externí CA je
  nutné do CEB portálu přidat ručně.

  Požadavky doložené v příručce:

  - podporovaní vydavatelé: I.CA, PostSignum, interní ČSOB CEB Business Connector CA;
  - podpis SHA256 nebo silnější;
  - RSA minimálně 2048 bitů;
  - pokud je přítomno Key Usage: digitální podpis nebo výměna klíčů;
  - pokud je přítomno Extended Key Usage: SSL klientská autentizace;
  - TLS doporučeno 1.3, minimum 1.2;
  - serverový certifikát banky má subjekt CN=ceb-bc.csob.cz; ostatní atributy nejsou
    určeny.
  - vydavatel serverového certifikátu banky má být standardní důvěryhodná certifikační
    autorita evidovaná ve Windows.
  - CA certifikát vydavatele klientského certifikátu není podle příručky doporučeno
    instalovat jako globálně důvěryhodný certifikát OS, pokud to není nutné pro platformu
    nebo implementaci.

  Bezpečnost:

  - privátní klíč chmod 400 nebo 600;
  - vlastník servisní uživatel;
  - žádné klíče v Docker image;
  - hesla z env/secret manageru;
  - audit expirace certifikátu při startu a periodicky;
  - při kompromitaci revokovat u CA, pokud je certifikát od I.CA/PostSignum, a blokovat/
    odebrat v CEB portálu;
  - certifikáty vydané bankou podle příručky nemají revokační mechanismus, blokace
    probíhá v CEB portálu.
  - samotná záloha souboru `.crt` nebo `.cer` nestačí, protože neobsahuje privátní klíč;
    pro obnovu provozu je potřeba záloha certifikátu včetně privátního klíče, typicky
    PKCS#12 `.pfx` nebo `.p12`.
  - pokud je certifikát používán ve více kontraktech, musí se při kompromitaci zablokovat
    nebo odebrat u všech smluv.

  ## 16. Download Manager Design

  Pravidla:

  - profil cursoru = hash environment + contract_number + filter + client_app_guid +
    certificate_fingerprint;
  - PrevQueryTimestamp se bere ze state;
  - pokud `PrevQueryTimestamp` není na vstupu uveden, banka použije podle příručky čas
    45 dní zpět;
  - na časový údaj starší než 45 dní v minulosti se nepřihlíží;
  - všechny časové hodnoty posílat jako `xsd:dateTime` ve formátu
    `YYYY-MM-DDTHH:MM:SS+ZZ:ZZ`;
  - pro konzistentní monitoring nových souborů musí SDK mezi voláními zachovat stejný
    `ContractNumber` a stejný `Filter`;
  - po SOAP chybě se cursor neposouvá;
  - pokud existuje soubor ve stavu R nebo bez URL, cursor se neposouvá;
  - soubory ve stavu D lze mezitím stáhnout;
  - soubor ve stavu F se zapíše jako permanentní chyba;
  - QueryTimestamp se uloží jako nový cursor až po bezpečném zpracování celé dávky podle
    pravidel SDK.

  Doložené download typy a formáty:

  | Typ | Význam | Formáty podle příručky |
  |---|---|---|
  | `VYPIS` | výpisy z účtů | `PDF`, `TXT`, `XML`, `BBGPC`, `BBMT940`, `BBTXT`, `BBBBF`, `SEPAXML` |
  | `AVIZO` | avíza plateb | `MT942`, `BBF`, `CAMT052` |
  | `KURZY` | kurzovní lístky ČNB a ČSOB | `FileFormat` se ignoruje / nebude uveden |
  | `IMPPROT` | protokoly o importu | TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB |

  Kurzovní lístky podle příručky:

  - zpráva typu `QUOTES`;
  - jméno souboru ČNB: `EXRT_CNB_yyyymmdd.BBF`;
  - jméno souboru ČSOB: `EXRT_CSOB_yyyymmdd.BBF`.

  SOAP `FileDetail` pole, která má SDK mapovat:

  - `Url`, volitelné; chybí při přípravě nebo chybě přípravy;
  - `Filename`;
  - `Type`;
  - `Format`, u kurzovních lístků nebude uveden;
  - `CreationDateTime`;
  - `Size`;
  - `UploadFileHash`, volitelné a jen u importních protokolů;
  - `Status` s hodnotami `R`, `D`, `F`.

  Doporučený model:

  - manager thread volá SOAP a plní download queue;
  - downloader worker stahuje REST URL;
  - stav každého souboru se ukládá před a po REST transferu;
  - atomický zápis brání polovičním souborům po crashi.

  ## 17. Upload Manager Design

  Workflow:

  1. Explicitní volání nebo directory watcher najde soubor.
  2. SDK spočítá SHA256.
  3. SDK zkontroluje lokální idempotency záznam.
  4. Zavolá StartUploadFileList v3.
  5. Pro status U nahraje multipart POST.
  6. Z REST JSON uloží NewFileId.
  7. Zavolá FinishUploadFileList v2.
  8. Pro status I naplánuje import protocol polling.
  9. Pro status R uloží odmítnutí a stejný upload neopakuje bez zásahu.

  `StartUploadFileList v3` vstupní metadata podle příručky:

  | Pole | Pravidlo |
  |---|---|
  | `Filename` | jméno souboru včetně přípony, omezeno na 50 znaků |
  | `Hash` | SHA256 obsahu souboru, 64 hex znaků |
  | `Size` | velikost v bajtech |
  | `Format` | jeden z doložených importních formátů |
  | `Separator` | volitelné; `|`, `/`, `:`, `::`, `;`, `;;`; pokud chybí, jde o pevnou šířku polí |
  | `Mode` | `IncludeIncorrect`, `OnlyCorrect`, `AllOrNothing`, `SignedAllOrNothing` |
  | `SkipCheckDuplicates` | volitelné `true/false`, default `false` |

  Doložené upload formáty:

  - `ABO`
  - `DUZ`
  - `MC TPS`
  - `MC ZPS`
  - `TXT TPS`
  - `TXT ZPS`
  - `XLS TPS`
  - `XLS ZPS`
  - `XLSX TPS`
  - `XLSX ZPS`
  - `MT101`
  - `XML SEPA`
  - `XML TPS`
  - `XML ZPS`

  `StartUploadFileList v3` výstupní statusy:

  | Status | Význam podle příručky | SDK behavior |
  |---|---|---|
  | `R` | odmítnuto, například již importováno | zalogovat, nepokračovat v REST uploadu |
  | `U` | možno zahájit upload podle URL | uložit URL a pokračovat multipart POST |

  SkipCheckDuplicates:

  - default false;
  - pokud true, banka podle příručky neprovede kontrolu stejného obsahu za posledních 30
    dní;
  - pro SignedAllOrNothing se kontrola duplicit vypnout nedá a příznak je ignorován.

  Crash recovery:

  - po StartUploadFileList uložit URL a metadata;
  - po REST uploadu okamžitě uložit NewFileId;
  - pokud crash nastane po REST uploadu a před finish, pokračovat FinishUploadFileList;
  - pokud REST upload skončil nejasně bez parsovatelného NewFileId, označit stav jako
    ambiguous a neuploadovat naslepo znovu.

  `FinishUploadFileList v2` vstup a výstup podle příručky:

  - vstup: `ContractNumber`, `ClientAppGuid`, seznam `FileId` s `Filename`, `Hash`,
    `NewFileId`;
  - `Hash` je SHA256, 64 hex znaků;
  - výstup obsahuje `FileStatus` s `Filename`, `Hash`, `Status` a `TicketId`;
  - status `R`: odmítnuto, například již jednou importováno nebo vadný podpis; zapsat do
    logu a neopakovat stejný upload bez zásahu;
  - status `I`: import zahájen; naplánovat stažení protokolu o importu.

  ## 18. Import Protocol Workflow

  Spuštění:

  - po FinishUploadFileList v2 se stavem I;
  - vytvořit ImportProtocolRecord se SHA256 hashem uploadu, filename, ClientAppGuid,
    NewFileId.

  Polling:

  - použít GetDownloadFileList v4;
  - filtrovat FileTypes = ["IMPPROT"];
  - použít ClientAppGuid, protože příručka uvádí, že filtr přidá soubory vytvořené pro
    danou instanci klientské aplikace;
  - párovat podle UploadFileHash, pokud je v odpovědi přítomen.

  Detaily z příručky:

  - importní protokol je dostupný později, protože zpracování uploadu je asynchronní;
  - protokol o importu je soubor typu `IMPPROT`;
  - `FileDetail/UploadFileHash` je volitelný a jen u protokolů o importu;
  - ve verzi v4 má `UploadFileHash` formát SHA256; starší protokoly mohou mít historickou
    MD5 hodnotu doplněnou mezerami;
  - formát protokolu o importu je `pain.002` ČSOB, dokumentovaný samostatným ZIP balíkem
    `protokol-pain.zip`.

  TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda existují další doporučené
  filtry pro importní protokoly kromě IMPPROT, ClientAppGuid a párování přes
  UploadFileHash.

  ## 19. State Storage And Idempotency Design

  MVP:

  - JSONL nebo SQLite;
  - pro MVP preferuji SQLite, protože transakce jsou zásadní.

  Production:

  - SQLite s WAL pro single-host deployment;
  - SQLAlchemy backend pro PostgreSQL/MS SQL v enterprise prostředí.

  Návrh tabulek:

  | Tabulka | Účel |
  |---|---|
  | profiles | cursor last_query_timestamp per contract/filter/profile |
  | download_files | filename, type, format, size, status, url hash, local path |
  | download_attempts | REST GET pokusy a výsledky |
  | upload_attempts | filename, hash, size, format, mode, stav workflow |
  | upload_rest_results | NewFileId, HTTP status, JSON status |
  | upload_finish_results | finish status I/R, TicketId |
  | import_protocols | stav pollingu, UploadFileHash, local path |
  | idempotency_keys | prevence opakovaného uploadu |
  | failures | retryable/permanent/ambiguous chyby |

  Transaction boundaries:

  - SOAP response + enqueue v jedné transakci;
  - REST success + file rename + state update jako co nejkratší kritická sekce;
  - NewFileId uložit před FinishUploadFileList;
  - cursor posunout až po potvrzení bezpečného zpracování.

  ## 20. Configuration Model

  YAML příklad:

  environment: production
  contract_number: "TODO"
  client_app_guid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

  certificate:
    cert_file: "/etc/csob/bccert.crt"
    key_file: "/etc/csob/bccert.key"
    ca_bundle: null

  state_url: "sqlite:////var/lib/csob-ceb/state.db"

  timeouts:
    connect_seconds: 10
    read_seconds: 120
    write_seconds: 120
    pool_seconds: 10

  rate_limit:
    soap_calls: 30
    per_seconds: 1200
    default_poll_seconds: 60

  logging:
    level: INFO
    redact_contract_number: true

  Environment enum:

  - production
  - demo

  Demo prostředí podle příručky:

  - má stejné SOAP a REST rozhraní jako produkce, liší se doménová část URL;
  - odpovědi jsou statické nebo částečně generované jednoduchými pravidly;
  - neudržuje stav mezi voláními;
  - ignoruje `ContractNumber`;
  - ignoruje kritéria filtrování v `GetDownloadFileList`;
  - nevyžaduje dodržování ochranného intervalu;
  - vyžaduje certifikátovou autentizaci, ale certifikát nemá vliv na obsah zpráv;
  - akceptuje certifikáty stejných CA jako produkce včetně interních ČSOB a testovacích
    certifikátů těchto CA;
  - nevyžaduje registraci certifikátu v CEB a podle příručky není nutné mít CEB zřízený.

  TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda existují další oficiální
  prostředí.

  ## 21. Error Model And Exception Hierarchy

  class CsobBCError(Exception): ...
  class CsobBCConfigError(CsobBCError): ...
  class CsobBCCertificateError(CsobBCError): ...
  class CsobBCSoapError(CsobBCError): ...
  class CsobBCSoapFault(CsobBCSoapError): ...
  class CsobBCHttpError(CsobBCError): ...
  class CsobBCRetryableError(CsobBCError): ...
  class CsobBCPermanentError(CsobBCError): ...
  class CsobBCRateLimitError(CsobBCRetryableError): ...
  class CsobBCDownloadError(CsobBCError): ...
  class CsobBCUploadError(CsobBCError): ...
  class CsobBCDuplicateUploadError(CsobBCPermanentError): ...
  class CsobBCStateError(CsobBCError): ...
  class CsobBCProtocolError(CsobBCError): ...

  Každá výjimka má nést:

  - operation;
  - contract_number_redacted;
  - ticket_id;
  - retryable;
  - permanent;
  - cause;
  - safe_message.

  ## 22. Error Mapping Tables

  SOAP Faulty:

  | Code | Význam dle příručky | SDK behavior |
  |---|---|---|
  | 1000 | obecná chyba serveru | retryable, backoff, log TicketId |
  | 1002 | kontrakt nemá povolen Business Connector | permanent, zastavit profil |
  | 1011 | certifikát není registrován / kontrakt neexistuje nebo není aktivní | permanent, zásah operátora |
  | 1012 | certifikát blokován | permanent, security incident |
  | 1101 | nadměrný počet volání | rate limit circuit open, dlouhý cooldown |

  SOAP business statusy v odpovědích:

  | Operace | Status | Význam dle příručky | SDK behavior |
  |---|---|---|---|
  | `GetDownloadFileList v4` | `R` | soubor se připravuje | ponechat původní `PrevQueryTimestamp`, opakovat později |
  | `GetDownloadFileList v4` | `D` | lze stáhnout podle URL | zařadit do download queue |
  | `GetDownloadFileList v4` | `F` | permanentní chyba přípravy souboru | zalogovat, permanent failure |
  | `StartUploadFileList v3` | `R` | odmítnuto, například již importováno | zalogovat, nepokračovat REST uploadem |
  | `StartUploadFileList v3` | `U` | lze uploadovat podle URL | provést multipart REST POST |
  | `FinishUploadFileList v2` | `R` | odmítnuto, například již jednou importováno nebo vadný podpis | zalogovat, neopakovat stejný upload bez zásahu |
  | `FinishUploadFileList v2` | `I` | import zahájen | založit import protocol polling |

  REST download HTTP:

  | HTTP | Význam dle příručky | SDK behavior |
  |---|---|---|
  | 200 | OK | uložit soubor |
  | 400 | URL expirovalo, soubor lze stáhnout jen 15 dní | permanent |
  | 401 | chyba autorizace | permanent/security |
  | 404 | soubor expiroval, 15 dní | permanent |
  | 500 | interní chyba serveru | retryable |
  | 503 | služba nedostupná | retryable, circuit breaker |

  REST upload HTTP:

  | HTTP | Význam dle příručky | SDK behavior |
  |---|---|---|
  | 200 | OK, kontrolovat JSON Status | podle JSON |
  | 201 | soubor vytvořen | success, uložit NewFileId |
  | 400 | chybí povinné parametry / soubor neexistuje | permanent |
  | 401 | chyba autorizace | permanent/security |
  | 403 | neautorizováno / URL expirovalo | permanent |
  | 408 | timeout | retryable |
  | 500 | interní chyba | retryable |
  | 502 | gateway chyba | retryable |
  | 503 | služba nedostupná | retryable |
  | 504 | timeout | retryable |

  REST upload JSON Status:

  | JSON Status | Význam dle příručky | SDK behavior |
  |---|---|---|
  | 201 | úspěch, NewFileId | success |
  | 450 | překročena velikost | permanent |
  | 451 | nepovolená přípona | permanent |
  | 452 | nepovolený typ | permanent |
  | 453 | antivirová kontrola selhala | permanent/security |
  | 454 | nepovolený tvar URL/obsahu nebo Content-Type | permanent |
  | 455 | timeout | retryable |
  | 456 | timeout | retryable |

  SSL/TLS:

  | Chyba | SDK behavior |
  |---|---|
  | expirovaný klientský certifikát | permanent před voláním |
  | blokovaný certifikát | očekávaně SOAP 1012 nebo TLS failure, permanent |
  | nevalidní serverový certifikát | permanent/security, nepovolovat verify=False |
  | TLS handshake failure | klasifikovat podle příčiny, default permanent pokud jde o certifikát/protokol |
  | nedostupná CRL/OCSP | TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB |

  Network:

  | Chyba | SDK behavior |
  |---|---|
  | DNS error | retryable s backoffem, po limitu outage |
  | connect timeout | retryable |
  | read timeout | retryable; u uploadu respektovat dokumentované timeout retry statusy |
  | connection reset | retryable |
  | malformed REST upload JSON | ambiguous protocol error, neopakovat slepě bez `NewFileId` |

  ## 23. Retry, Timeout, Polling, Protective Interval Strategy

  Rate limiter:

  - token bucket per ContractNumber + certificate fingerprint;
  - default 30 tokenů / 1200 sekund podle příručky;
  - doporučený běžný polling interval: 60 sekund nebo delší;
  - pro více workflow sdílet jeden SOAP budget.
  - limit je sledován pro konkrétní dvojici číslo smlouvy / klientský přístupový
    certifikát;
  - pokud běží více klientských aplikací se stejným kontraktem a stejným certifikátem,
    sdílejí bankovní limit a mohou si navzájem vyvolat SOAP Fault `1101`;
  - příručka doporučuje pro každou instalaci klientské aplikace jiný certifikát, pokud by
    jinak docházelo k souběhu volání.

  TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk CEB, zda banka doporučuje konkrétní
  minimální rozestup mezi dvěma SOAP voláními mimo okno 30/20.

  Retry policies:

  | Operace | Retry |
  |---|---|
  | SOAP 1000 | exponential backoff + jitter |
  | SOAP 1101 | cooldown alespoň ochranné okno + jitter, circuit open |
  | HTTP 503 | retry s circuit breakerem; příručka ho uvádí pro odstávku služby |
  | REST download 500/503 | retry |
  | REST upload 408/500/502/503/504 a JSON 455/456 | retry |
  | FinishUploadFileList SOAP 1000 | retry, protože REST upload už proběhl |
  | Finish status R | neretryovat stejný upload bez zásahu |

  Timeouts:

  - connect 10 s;
  - read download podle velikosti, default 120 s;
  - upload write/read 120 s;
  - vše konfigurovatelné.

  ## 24. Logging, Audit Trail, Observability

  Logovat:

  - operation name;
  - environment;
  - redacted contract;
  - certificate fingerprint prefix;
  - ClientAppGuid;
  - TicketId;
  - filename;
  - SHA256 hash souboru;
  - workflow state;
  - retry attempt;
  - duration.

  Nelze logovat:

  - privátní klíč;
  - PFX heslo;
  - plný certifikát;
  - obsah bankovních souborů;
  - celé REST URL, pokud obsahuje citlivý token. Doporučení: logovat hash URL.

  Metrics:

  - SOAP calls per contract/cert;
  - 1101 count;
  - download success/failure;
  - upload stages;
  - import protocol latency;
  - certificate days to expiry;
  - queue depth.

  ## 25. Security Recommendations

  Threat model:

  - krádež privátního klíče;
  - duplicitní odeslání platební dávky;
  - únik bankovních souborů z logů;
  - podvržení serveru při vypnuté validaci certifikátu;
  - stavová korupce po crashi;
  - supply-chain kompromitace dependencies.

  Doporučení:

  - nikdy nepoužívat verify=False;
  - privátní klíče mimo repo a image;
  - strict permissions;
  - oddělený servisní uživatel;
  - záloha certifikátu včetně privátního klíče;
  - pravidelný cert expiry check;
  - rotation runbook;
  - SBOM pro release artifact;
  - pinned/minimum dependency versions;
  - pip-audit nebo ekvivalent v CI;
  - redakce logů testovaná regresními testy.

  ## 26. Deployment Models

  | Model | Vhodnost |
  |---|---|
  | Lokální server | vhodné pro malé firmy, jednoduchá obsluha certifikátu |
  | systemd service | doporučené pro Linux produkci |
  | cron job | vhodné pro jednoduchý polling, horší pro queue/retry |
  | container | vhodné, pokud secrets a persistent state nejsou v image |
  | ERP plugin | vhodné pro těsnou integraci, nutná izolace certifikátu |
  | Windows Scheduled Task | vhodné pro Windows prostředí s PFX/cert store |
  | Kubernetes CronJob | vhodné jen pokud organizace má K8s a správně řeší secrets, mTLS a persistent state |

  ## 27. Background Workers And Queues

  MVP:

  - in-process queue;
  - jeden scheduler loop;
  - SQLite state;
  - single process lock.

  Production:

  - persistent queue v SQLite/Postgres;
  - download-poller;
  - download-worker;
  - upload-worker;
  - import-protocol-worker;
  - globální rate limiter pro SOAP;
  - leader lock per contract/cert.

  ## 28. Testing Strategy

  Testy:

  - unit testy modelů a validací;
  - mocked SOAP testy přes fixture XML/WSDL;
  - mocked REST GET/POST přes respx, responses nebo requests-mock;
  - contract testy proti aktuálnímu WSDL/XSD;
  - demo/sandbox testy s reálným mTLS certifikátem, pokud je k dispozici;
  - cert fixtures: expirovaný cert, neodpovídající key, PFX;
  - TLS failure testy;
  - retry testy pro 1000, 1101, 500, 503, 455, 456;
  - crash recovery testy;
  - idempotency testy;
  - regression testy pro R, D, F, U, I;
  - security testy redakce logů.

  ## 29. CI/CD And Packaging Recommendation

  Pipeline:

  - ruff check;
  - ruff format --check;
  - mypy;
  - pytest;
  - coverage;
  - python -m build;
  - twine check;
  - dependency audit;
  - SBOM generation.

  Release:

  - semantic versioning;
  - changelog;
  - signed git tag;
  - artifact signing, pokud to interní governance vyžaduje;
  - oddělené release notes pro breaking změny ČSOB WSDL/API.

  ## 30. Documentation Plan

  Dokumentace:

  - README quickstart;
  - certificate setup guide;
  - PEM/KEY/PFX guide;
  - configuration guide;
  - download examples;
  - upload examples;
  - import protocol workflow;
  - troubleshooting guide;
  - SOAP Fault reference;
  - REST error reference;
  - security guide;
  - ERP integration guide;
  - operations runbook;
  - recovery procedures.

  ## 31. Mermaid Sequence Diagram: Download Workflow

  ```mermaid
  sequenceDiagram
      participant ERP
      participant SDK
      participant State
      participant SOAP as ČSOB SOAP
      participant REST as ČSOB REST

      ERP->>SDK: download_new_files(filter)
      SDK->>State: load PrevQueryTimestamp
      SDK->>SOAP: GetDownloadFileList v4
      SOAP-->>SDK: QueryTimestamp, FileList, TicketId

      loop každý soubor
          alt Status R nebo URL chybí
              SDK->>State: ponechat původní PrevQueryTimestamp
          else Status D
              SDK->>REST: GET URL
              REST-->>SDK: 200 file stream
              SDK->>State: uložit downloaded record
          else Status F
              SDK->>State: permanent failure
          end
      end

      alt vše bezpečně zpracováno
          SDK->>State: uložit QueryTimestamp jako nový cursor
      else unresolved files
          SDK->>State: ponechat původní cursor
      end
  ```

  ## 32. Mermaid Sequence Diagram: Upload Workflow

  ```mermaid
  sequenceDiagram
      participant ERP
      participant SDK
      participant State
      participant SOAP as ČSOB SOAP
      participant REST as ČSOB REST

      ERP->>SDK: upload_payment_batch(file, metadata)
      SDK->>SDK: compute SHA256
      SDK->>State: create upload attempt
      SDK->>SOAP: StartUploadFileList v3
      SOAP-->>SDK: Status U/R, URL, TicketId

      alt Status R
          SDK->>State: rejected, no automatic retry
      else Status U
          SDK->>REST: POST multipart/form-data
          REST-->>SDK: JSON Status, NewFileId
          SDK->>State: save NewFileId
          SDK->>SOAP: FinishUploadFileList v2
          SOAP-->>SDK: Status I/R, TicketId

          alt Status I
              SDK->>State: import protocol pending
          else Status R
              SDK->>State: rejected, no repeat without intervention
          end
      end
  ```

  ## 33. Mermaid Sequence Diagram: Import Protocol Workflow

  ```mermaid
  sequenceDiagram
      participant SDK
      participant State
      participant SOAP as ČSOB SOAP
      participant REST as ČSOB REST
      participant ERP

      SDK->>State: load pending import protocols
      SDK->>SOAP: GetDownloadFileList v4 filter IMPPROT + ClientAppGuid
      SOAP-->>SDK: FileList with UploadFileHash

      loop protokoly
          alt hash odpovídá uploadu a Status D
              SDK->>REST: GET URL
              REST-->>SDK: protocol file
              SDK->>State: mark protocol downloaded
              SDK->>ERP: report import protocol available
          else Status R nebo URL chybí
              SDK->>State: keep pending
          else Status F
              SDK->>State: protocol failure
          end
      end
  ```

  ## 34. Production Checklist

  - Certifikát registrovaný v CEB.
  - Služba Business Connector povolená u smlouvy.
  - V CEB povolené konkrétní operace: kurzovní lístky, výpisy pro konkrétní účty, avíza
    pro konkrétní účty, upload platebních dávek pro konkrétní účty a případně upload
    podepsaných platebních dávek.
  - Správné ContractNumber.
  - Správný ClientAppGuid.
  - Ověřené prod/demo prostředí.
  - Ověřené, že aplikace používá `GetDownloadFileList v4`, `StartUploadFileList v3` a
    `FinishUploadFileList v2`.
  - Ověřené, že upload používá SHA256 a pouze multipart.
  - Privátní klíč má práva 400 nebo 600.
  - Záloha certifikátu obsahuje i privátní klíč, například bezpečně uložený `.pfx/.p12`.
  - Server certificate validation zapnutá.
  - TLS minimum 1.2, preferovaně TLS 1.3.
  - CA bundle nastavený, pokud prostředí nemá správný trust store.
  - State store zálohovaný.
  - Rate limiter nastaven na 30/20 nebo konzervativněji.
  - Ověřeno, že neběží více instancí se stejným kontraktem a certifikátem bez sdíleného
    rate limiteru.
  - Monitoring a alerting zapnuté.
  - Log redaction ověřená.
  - Crash recovery otestované.
  - Import protocol polling otestovaný.
  - Ověřené chování při `1101`, HTTP `503`, expirované download URL a odmítnutém uploadu.
  - Runbook pro blokovaný/kompromitovaný certifikát připravený.

  ## 35. Implementation Roadmap

  Prototype:

  - načíst WSDL;
  - zavolat demo SOAP s mTLS;
  - REST GET/POST mock;
  - základní Pydantic modely.

  MVP:

  - sync klient;
  - SQLite state;
  - download workflow;
  - upload workflow;
  - import protocol polling;
  - retry/rate limit;
  - CLI examples.

  Production-ready v1.0:

  - robustní error mapping;
  - audit logs;
  - certificate validation;
  - crash recovery;
  - CI/CD;
  - dokumentace;
  - sandbox test profile.

  Advanced v2:

  - SQLAlchemy backend;
  - async REST workers;
  - ERP plugin adapters;
  - metrics exporters;
  - persistent distributed queue;
  - operational dashboard.

  ## 36. Risks And Mitigation Plan

  | Riziko | Mitigace |
  |---|---|
  | Nedokumentované chování ČSOB | TODO položky, testy v demo, eskalace Helpdesk CEB |
  | Změny WSDL | contract tests, versioned SOAP layer |
  | Expirace certifikátu | monitoring a alerting |
  | Blokovaný certifikát | permanent error, security runbook |
  | Rate limit lockout | token bucket, circuit breaker po 1101 |
  | Duplicitní upload | SHA256 idempotency, state store, neopakovat ambiguous POST |
  | Partial upload failure | stage-based recovery |
  | Chybějící import protokol | pending state, alert po SLA; TODO ověřit SLA |
  | ERP chyby | explicitní status API a retry-safe reporting |
  | State corruption | SQLite transactions, WAL, backup |
  | Únik citlivých dat | log redaction, no file content logging |
  | Nejasné vlastnictví provozu | operations runbook a alert routing |

  ## 37. Final Recommended Architecture

  Doporučená implementace je synchronní Python SDK s zeep pro SOAP, httpx nebo requests
  pro REST přenosy, pydantic pro konfiguraci/modely, cryptography pro certifikáty,
  tenacity nebo vlastní policy pro retry a SQLite jako výchozí produkčně použitelný state
  store.

  Nejdůležitější implementační pravidla:

  - SOAP řídí proces, REST pouze přenáší soubory.
  - REST URL se nikdy neskládají ručně.
  - PrevQueryTimestamp se posouvá pouze po bezpečném zpracování.
  - Upload je stavový proces: start → REST upload → uložit NewFileId → finish → import
    protocol polling.
  - Rate limiter je centrální a sdílený pro všechny SOAP operace stejného kontraktu/
    certifikátu.
  - Chyby se klasifikují jako retryable, permanent nebo ambiguous.
  - Certifikáty a klíče jsou bezpečnostní boundary, ne běžná konfigurace.
  - Všechny neověřené detaily zůstávají TODO: ověřit v dokumentaci nebo s ČSOB Helpdesk
    CEB.

  Zdroje:

  - Oficiální stránka ČSOB Business Connector:
    https://www.csob.cz/firmy/prehled-on-line-kanalu-a-aplikaci/business-connector
  - WSDL ZIP uvedený v příručce:
    https://www.csob.cz/portal/documents/10710/15100026/cebbc-wsdl.zip
  - Přiložená implementační příručka: /Users/samuel/Downloads/csob-business-connector-
    implementacni-prirucka.pdf
