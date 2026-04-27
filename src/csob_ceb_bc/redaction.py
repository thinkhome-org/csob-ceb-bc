import re


def redact_contract(contract_number: str) -> str:
    if len(contract_number) <= 3:
        return contract_number
    return contract_number[:3] + "***"


def redact_url(url: str) -> str:
    # Simple redaction of common query parameters
    sensitive_params = ["token", "auth", "key", "secret", "password"]
    for param in sensitive_params:
        url = re.sub(
            rf"({param}=)[^&]*",
            r"\1***",
            url,
            flags=re.IGNORECASE,
        )
    return url
