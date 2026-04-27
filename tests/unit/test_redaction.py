from csob_ceb_bc.redaction import redact_contract, redact_url


def test_redact_contract():
    assert redact_contract("123456789") == "123***"
    assert redact_contract("12") == "12"


def test_redact_url():
    assert (
        redact_url("https://example.com/path?token=secret") == "https://example.com/path?token=***"
    )
