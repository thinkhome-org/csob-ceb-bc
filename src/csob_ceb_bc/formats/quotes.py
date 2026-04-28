"""Fixed-width parser for ČSOB BC exchange-rate files (QUOTES format).

Specification from ČSOB BC implementation guide (strana 24–25).
Encoding is typically CP1250.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator


class QuotesHeader(BaseModel):
    """Record type 01 – header (32 characters)."""

    bank_app: str  # position 1, length 1 – const "T"
    client_id: str  # position 2-9, length 8
    message_type: str  # position 10-15, length 6 – const "QUOTES"
    separator: str  # position 16, length 1 – space
    record_type: str  # position 17-18, length 2 – "01"
    message_id: str  # position 19-32, length 14

    model_config = {"frozen": True}


class QuotesMetadata(BaseModel):
    """Record type 02 – metadata (76 characters)."""

    bank_app: str  # position 1, length 1 – const "N"
    client_id: str  # position 2-9, length 8
    message_type: str  # position 10-15, length 6 – "QUOTES"
    separator: str  # position 16, length 1 – space
    record_type: str  # position 17-18, length 2 – "02"
    sequence_no: int | None  # position 19-21, length 3
    valid_from: date  # position 22-29, length 8 – CCYYMMDD
    provider_name: str  # position 30-64, length 35
    timestamp: str  # position 65-76, length 12

    model_config = {"frozen": True}

    @field_validator("valid_from", mode="before")
    @classmethod
    def _parse_valid_from(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        v = str(v).strip()
        return datetime.strptime(v, "%Y%m%d").date()


class QuotesRate(BaseModel):
    """Record type 03 – rate per currency (124 characters)."""

    bank_app: str  # position 1, length 1 – const "N"
    client_id: str  # position 2-9, length 8
    message_type: str  # position 10-15, length 6 – "QUOTES"
    separator: str  # position 16, length 1 – space
    record_type: str  # position 17-18, length 2 – "03"
    country: str  # position 19-53, length 35
    amount: int  # position 54-57, length 4
    filler2: str  # position 58-59, length 2
    currency_code: str  # position 60-62, length 3
    filler3: str  # position 63, length 1
    deviza_buy: Decimal  # position 64-73, length 10 (6+3 with decimal point)
    deviza_sell: Decimal  # position 74-83, length 10
    deviza_mid: Decimal  # position 84-93, length 10
    filler4: str  # position 94, length 1
    valuta_buy: Decimal  # position 95-104, length 10
    valuta_sell: Decimal  # position 105-114, length 10
    valuta_mid: Decimal  # position 115-124, length 10

    model_config = {"frozen": True}

    @field_validator(
        "deviza_buy",
        "deviza_sell",
        "deviza_mid",
        "valuta_buy",
        "valuta_sell",
        "valuta_mid",
        mode="before",
    )
    @classmethod
    def _parse_rate(cls, v: Any) -> Decimal:
        if isinstance(v, Decimal):
            return v
        v = str(v).strip().replace(" ", "")
        return Decimal(v)

    @field_validator("amount", mode="before")
    @classmethod
    def _parse_amount(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        return int(str(v).strip())


class QuotesFile(BaseModel):
    """Parsed QUOTES file (kurzovní lístek)."""

    header: QuotesHeader
    metadata: QuotesMetadata
    rates: list[QuotesRate]

    model_config = {"frozen": True}


def _parse_header(line: str) -> QuotesHeader:
    if len(line) < 32:
        raise ValueError(f"QUOTES header too short: {len(line)} chars (expected 32)")
    return QuotesHeader(
        bank_app=line[0:1],
        client_id=line[1:9],
        message_type=line[9:15],
        separator=line[15:16],
        record_type=line[16:18],
        message_id=line[18:32],
    )


def _parse_metadata(line: str) -> QuotesMetadata:
    if len(line) < 76:
        raise ValueError(f"QUOTES metadata too short: {len(line)} chars (expected 76)")
    return QuotesMetadata.model_validate(
        {
            "bank_app": line[0:1],
            "client_id": line[1:9],
            "message_type": line[9:15],
            "separator": line[15:16],
            "record_type": line[16:18],
            "sequence_no": line[18:21].strip() or None,
            "valid_from": line[21:29],
            "provider_name": line[29:64].strip(),
            "timestamp": line[64:76].strip(),
        }
    )


def _parse_rate(line: str) -> QuotesRate:
    if len(line) < 124:
        raise ValueError(f"QUOTES rate too short: {len(line)} chars (expected 124)")
    return QuotesRate.model_validate(
        {
            "bank_app": line[0:1],
            "client_id": line[1:9],
            "message_type": line[9:15],
            "separator": line[15:16],
            "record_type": line[16:18],
            "country": line[18:53].strip(),
            "amount": line[53:57],
            "filler2": line[57:59],
            "currency_code": line[59:62].strip(),
            "filler3": line[62:63],
            "deviza_buy": line[63:73],
            "deviza_sell": line[73:83],
            "deviza_mid": line[83:93],
            "filler4": line[93:94],
            "valuta_buy": line[94:104],
            "valuta_sell": line[104:114],
            "valuta_mid": line[114:124],
        }
    )


def parse_quotes(content: str | bytes, encoding: str = "cp1250") -> QuotesFile:
    """Parse a ČSOB BC exchange-rate file in QUOTES fixed-width format.

    Args:
        content: Raw file content (str or bytes).
        encoding: Text encoding if *content* is bytes (default ``cp1250``).

    Returns:
        Structured :class:`QuotesFile`.

    Raises:
        ValueError: If the file structure does not match the expected QUOTES format.
    """
    if isinstance(content, bytes):
        content = content.decode(encoding, errors="replace")

    lines = [ln.rstrip("\n\r") for ln in content.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("QUOTES file is empty")

    # Header (record 01) must be first
    header = _parse_header(lines[0])
    if header.record_type != "01":
        raise ValueError(
            f"Expected QUOTES header (01), got {header.record_type!r}"
        )

    # Metadata (record 02) must be second
    if len(lines) < 2:
        raise ValueError("QUOTES file missing metadata record (02)")
    metadata = _parse_metadata(lines[1])
    if metadata.record_type != "02":
        raise ValueError(
            f"Expected QUOTES metadata (02), got {metadata.record_type!r}"
        )

    # Remaining lines are rates (record 03)
    rates: list[QuotesRate] = []
    for line in lines[2:]:
        rate = _parse_rate(line)
        if rate.record_type != "03":
            raise ValueError(
                f"Expected QUOTES rate (03), got {rate.record_type!r}"
            )
        rates.append(rate)

    return QuotesFile(header=header, metadata=metadata, rates=rates)
