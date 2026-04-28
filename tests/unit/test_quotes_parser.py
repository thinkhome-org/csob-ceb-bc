"""Tests for QUOTES fixed-width exchange-rate parser."""

from decimal import Decimal

import pytest

from csob_ceb_bc.formats.quotes import QuotesFile, parse_quotes

# Exactly 32 chars header, 76 chars metadata, 124 chars rate lines
_SAMPLE = (
    "TTDCEB   QUOTES 0120180831057299\n"
    "NTDCEB   QUOTES 0216820180831CSOB                               201808310656\n"
    "NTDCEB   QUOTES 03AUSTRALIAN DOLLAR                  1     AUD     15.617"
    "    16.415    16.016      0.000     0.000     0.000\n"
    "NTDCEB   QUOTES 03SWISS FRANC                        1     CHF     22.244"
    "    23.385    22.815     22.244    23.385    22.815\n"
)


def test_parse_quotes_header():
    result = parse_quotes(_SAMPLE)
    assert result.header.bank_app == "T"
    assert result.header.client_id == "TDCEB   "
    assert result.header.message_type == "QUOTES"
    assert result.header.record_type == "01"
    assert result.header.message_id == "20180831057299"


def test_parse_quotes_metadata():
    result = parse_quotes(_SAMPLE)
    assert result.metadata.bank_app == "N"
    assert result.metadata.record_type == "02"
    assert result.metadata.sequence_no == 168
    assert result.metadata.valid_from.year == 2018
    assert result.metadata.valid_from.month == 8
    assert result.metadata.valid_from.day == 31
    assert result.metadata.provider_name == "CSOB"
    assert result.metadata.timestamp == "201808310656"


def test_parse_quotes_rates():
    result = parse_quotes(_SAMPLE)
    assert len(result.rates) == 2

    aud = result.rates[0]
    assert aud.country == "AUSTRALIAN DOLLAR"
    assert aud.currency_code == "AUD"
    assert aud.amount == 1
    assert aud.deviza_buy == Decimal("15.617")
    assert aud.deviza_sell == Decimal("16.415")
    assert aud.deviza_mid == Decimal("16.016")
    assert aud.valuta_buy == Decimal("0.000")
    assert aud.valuta_sell == Decimal("0.000")
    assert aud.valuta_mid == Decimal("0.000")

    chf = result.rates[1]
    assert chf.country == "SWISS FRANC"
    assert chf.currency_code == "CHF"
    assert chf.amount == 1
    assert chf.deviza_buy == Decimal("22.244")
    assert chf.valuta_mid == Decimal("22.815")


def test_parse_quotes_bytes_encoding():
    result = parse_quotes(_SAMPLE.encode("cp1250"))
    assert isinstance(result, QuotesFile)
    assert len(result.rates) == 2


def test_parse_quotes_empty():
    with pytest.raises(ValueError, match="empty"):
        parse_quotes("")


def test_parse_quotes_missing_metadata():
    with pytest.raises(ValueError, match="missing metadata"):
        parse_quotes("TTDCEB   QUOTES 0120180831057299\n")


def test_parse_quotes_wrong_header_type():
    bad = _SAMPLE.replace("01", "99", 1)
    with pytest.raises(ValueError, match="Expected QUOTES header"):
        parse_quotes(bad)
